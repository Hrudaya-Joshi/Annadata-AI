from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app.extensions import db
from app.models import (
    NGO, DonationRequest, FoodDonation, Volunteer,
    PickupAssignment, RescueMission, BeneficiaryDemand, AuditLog
)
from app.services.mission_service import MissionService
from app.services.emergency_service import EmergencyRescueService
from app.tools.geo_tools import calculate_distance_km

ngo_bp = Blueprint('ngo', __name__, url_prefix='/ngo')


def get_current_ngo():
    if current_user.role != 'ngo':
        flash('Access denied.', 'danger')
        return None
    ngo = NGO.query.filter_by(user_id=current_user.id).first()
    if not ngo:
        flash('NGO profile not found.', 'danger')
    return ngo


@ngo_bp.route('/dashboard')
@login_required
def dashboard():
    ngo = get_current_ngo()
    if not ngo:
        return redirect(url_for('main.home'))

    # All incoming requests for this NGO
    requests = DonationRequest.query.filter_by(
        ngo_id=ngo.id
    ).order_by(DonationRequest.requested_at.desc()).all()

    pending_requests = [r for r in requests if r.status == 'pending']
    accepted_requests = [r for r in requests if r.status == 'accepted']

    # Active Rescue Missions for this NGO
    active_missions = RescueMission.query.filter(
        RescueMission.ngo_id == ngo.id,
        RescueMission.status.notin_(['completed', 'cancelled'])
    ).order_by(RescueMission.updated_at.desc()).all()

    # Logged beneficiary demands
    demands = BeneficiaryDemand.query.filter_by(ngo_id=ngo.id, status='active').all()

    # Network emergency alerts
    emergency_alerts = EmergencyRescueService.scan_and_escalate(threshold_hours=2.0)

    # Compute NGO capacity utilization
    committed_servings = sum(
        m.donation.quantity for m in active_missions if m.donation and m.donation.unit != 'kg'
    )
    capacity_available = max(0, ngo.capacity_people - committed_servings)

    return render_template(
        'ngo/dashboard.html',
        ngo=ngo,
        requests=requests[:10],
        pending_requests=pending_requests,
        accepted_requests=accepted_requests,
        active_missions=active_missions,
        demands=demands,
        emergencies=emergency_alerts,
        capacity_available=capacity_available,
        committed_servings=committed_servings
    )


@ngo_bp.route('/donations')
@login_required
def donations():
    ngo = get_current_ngo()
    if not ngo:
        return redirect(url_for('main.home'))

    all_requests = DonationRequest.query.filter_by(
        ngo_id=ngo.id
    ).order_by(DonationRequest.requested_at.desc()).all()

    return render_template('ngo/donations.html', ngo=ngo, requests=all_requests)


@ngo_bp.route('/request/<int:request_id>')
@login_required
def request_detail(request_id):
    ngo = get_current_ngo()
    if not ngo:
        return redirect(url_for('main.home'))

    donation_request = DonationRequest.query.get_or_404(request_id)
    if donation_request.ngo_id != ngo.id and current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('ngo.dashboard'))

    donation = FoodDonation.query.get_or_404(donation_request.donation_id)
    mission = RescueMission.query.filter_by(donation_id=donation.id).first()

    return render_template(
        'ngo/request_detail.html',
        ngo=ngo,
        request=donation_request,
        donation=donation,
        mission=mission,
        safety=donation.safety_assessment
    )


@ngo_bp.route('/request/<int:request_id>/accept', methods=['POST'])
@login_required
def accept_request(request_id):
    ngo = get_current_ngo()
    if not ngo:
        return redirect(url_for('main.home'))

    donation_request = DonationRequest.query.get_or_404(request_id)
    if donation_request.ngo_id != ngo.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('ngo.dashboard'))

    if donation_request.status != 'pending':
        flash('This donation request has already been processed.', 'warning')
        return redirect(url_for('ngo.dashboard'))

    donation = donation_request.donation
    if not donation:
        flash('Linked donation record not found.', 'danger')
        return redirect(url_for('ngo.dashboard'))

    # CAPACITY CHECK: Prevent accepting beyond configured capacity!
    active_missions = RescueMission.query.filter(
        RescueMission.ngo_id == ngo.id,
        RescueMission.status.notin_(['completed', 'cancelled'])
    ).all()
    committed_servings = sum(m.donation.quantity for m in active_missions if m.donation and m.donation.unit != 'kg')

    if (committed_servings + donation.quantity) > (ngo.capacity_people * 1.25):
        flash(
            f'Capacity Limit Exceeded! Accepting this donation (+{donation.quantity}) would exceed your '
            f'configured capacity ({ngo.capacity_people} people). Current active commitment is {committed_servings}.',
            'danger'
        )
        return redirect(url_for('ngo.request_detail', request_id=request_id))

    try:
        # Check for available volunteer
        volunteer = Volunteer.query.filter_by(available=True).first()

        donation_request.status = 'accepted'
        donation_request.responded_at = datetime.utcnow()
        donation_request.response_notes = request.form.get('notes', 'Accepted by NGO')

        # Create or update tracked RescueMission
        mission = RescueMission.query.filter_by(donation_id=donation.id).first()
        if not mission:
            mission = MissionService.create_mission_for_request(donation, ngo, volunteer)
        else:
            mission.ngo_id = ngo.id
            if volunteer and not mission.volunteer_id:
                mission.volunteer_id = volunteer.id
                mission.status = 'volunteer_assigned'

        # Manage PickupAssignment
        assignment = PickupAssignment.query.filter_by(request_id=donation_request.id).first()
        if not assignment and volunteer:
            assignment = PickupAssignment(
                request_id=donation_request.id,
                volunteer_id=volunteer.id,
                status='assigned'
            )
            db.session.add(assignment)
            volunteer.available = False

        donation.status = 'matched'

        audit = AuditLog(
            user_id=current_user.id,
            action="ACCEPT_DONATION_REQUEST",
            target_type="DonationRequest",
            target_id=donation_request.id,
            details=f"NGO {ngo.organization_name} accepted donation #{donation.id}. Mission: {mission.mission_code}"
        )
        db.session.add(audit)
        db.session.commit()

        if volunteer:
            flash(f'Request accepted! Rescue Mission {mission.mission_code} created and assigned to Volunteer #{volunteer.id}.', 'success')
        else:
            flash(f'Request accepted! Rescue Mission {mission.mission_code} created. Awaiting volunteer dispatch.', 'info')

        return redirect(url_for('missions.mission_detail', mission_id=mission.id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error accepting request: {str(e)}', 'danger')
        return redirect(url_for('ngo.dashboard'))


@ngo_bp.route('/request/<int:request_id>/reject', methods=['POST'])
@login_required
def reject_request(request_id):
    ngo = get_current_ngo()
    if not ngo:
        return redirect(url_for('main.home'))

    donation_request = DonationRequest.query.get_or_404(request_id)
    if donation_request.ngo_id != ngo.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('ngo.dashboard'))

    reason = request.form.get('rejection_reason', 'Capacity / operational constraints').strip()

    try:
        donation_request.status = 'rejected'
        donation_request.responded_at = datetime.utcnow()
        donation_request.response_notes = reason

        audit = AuditLog(
            user_id=current_user.id,
            action="REJECT_DONATION_REQUEST",
            target_type="DonationRequest",
            target_id=donation_request.id,
            details=f"NGO {ngo.organization_name} rejected request #{donation_request.id}. Reason: {reason}"
        )
        db.session.add(audit)
        db.session.commit()

        flash('Donation request rejected with documented reason.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Error rejecting request: {str(e)}', 'danger')

    return redirect(url_for('ngo.dashboard'))


@ngo_bp.route('/demand/create', methods=['POST'])
@login_required
def create_demand():
    ngo = get_current_ngo()
    if not ngo:
        return redirect(url_for('main.home'))

    donation_category = (request.form.get('donation_category') or 'prepared_food').strip().lower()
    category = (request.form.get('category') or request.form.get('food_category') or 'cooked meals').strip()
    qty_val = request.form.get('required_quantity') or request.form.get('required_servings') or 50
    try:
        qty = int(qty_val)
    except (TypeError, ValueError):
        qty = 50
    unit = request.form.get('unit', 'meals' if donation_category == 'prepared_food' else 'kg')
    urgency = request.form.get('urgency_level') or request.form.get('urgency') or 'normal'
    notes = request.form.get('notes', '')

    demand = BeneficiaryDemand(
        ngo_id=ngo.id,
        donation_category=donation_category,
        category=category,
        required_quantity=qty,
        unit=unit,
        urgency_level=urgency,
        notes=notes
    )
    db.session.add(demand)
    db.session.commit()

    flash('Beneficiary demand logged successfully! The Smart Allocation Engine will prioritize matching donations.', 'success')
    return redirect(url_for('ngo.dashboard'))
