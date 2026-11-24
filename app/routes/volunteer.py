from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Volunteer, PickupAssignment, RescueMission, AuditLog
from app.services.mission_service import MissionService

volunteer_bp = Blueprint('volunteer', __name__, url_prefix='/volunteer')


def get_current_volunteer():
    if current_user.role != 'volunteer':
        flash('Access denied.', 'danger')
        return None
    vol = Volunteer.query.filter_by(user_id=current_user.id).first()
    if not vol:
        flash('Volunteer profile not found.', 'danger')
    return vol


@volunteer_bp.route('/dashboard')
@login_required
def dashboard():
    volunteer = get_current_volunteer()
    if not volunteer:
        return redirect(url_for('main.home'))

    # Active rescue missions assigned to this volunteer
    assigned_missions = RescueMission.query.filter(
        RescueMission.volunteer_id == volunteer.id,
        RescueMission.status.notin_(['completed', 'cancelled'])
    ).order_by(RescueMission.updated_at.desc()).all()

    completed_missions = RescueMission.query.filter(
        RescueMission.volunteer_id == volunteer.id,
        RescueMission.status.in_(['delivery_confirmed', 'completed'])
    ).order_by(RescueMission.delivery_time.desc()).all()

    # Legacy assignments for backward compatibility
    assignments = PickupAssignment.query.filter_by(
        volunteer_id=volunteer.id
    ).order_by(PickupAssignment.assigned_at.desc()).all()

    return render_template(
        'volunteer/dashboard.html',
        volunteer=volunteer,
        assigned_missions=assigned_missions,
        completed_missions=completed_missions,
        assignments=assignments
    )


@volunteer_bp.route('/toggle-availability', methods=['POST'])
@login_required
def toggle_availability():
    volunteer = get_current_volunteer()
    if not volunteer:
        return redirect(url_for('main.home'))

    volunteer.available = not volunteer.available
    db.session.commit()

    status_str = "Available for Dispatch" if volunteer.available else "Offline / Unavailable"
    flash(f'Your status is now: {status_str}.', 'info')
    return redirect(url_for('volunteer.dashboard'))


@volunteer_bp.route('/pickups')
@login_required
def pickups():
    volunteer = get_current_volunteer()
    if not volunteer:
        return redirect(url_for('main.home'))

    missions = RescueMission.query.filter_by(
        volunteer_id=volunteer.id
    ).order_by(RescueMission.created_at.desc()).all()

    return render_template('volunteer/pickups.html', volunteer=volunteer, missions=missions)


@volunteer_bp.route('/pickup/<int:assignment_id>/accept', methods=['POST'])
@login_required
def accept_pickup(assignment_id):
    volunteer = get_current_volunteer()
    if not volunteer:
        return redirect(url_for('main.home'))

    assignment = PickupAssignment.query.get_or_404(assignment_id)
    if assignment.volunteer_id != volunteer.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('volunteer.dashboard'))

    try:
        assignment.status = 'accepted'
        assignment.accepted_at = datetime.utcnow()

        # Update linked mission if exists
        req = assignment.request
        if req and req.donation:
            mission = RescueMission.query.filter_by(donation_id=req.donation.id).first()
            if mission:
                mission.status = 'volunteer_assigned'

        db.session.commit()
        flash('Pickup assignment accepted successfully! Please head to the donor location.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error accepting assignment: {str(e)}', 'danger')

    return redirect(url_for('volunteer.dashboard'))


@volunteer_bp.route('/pickup/<int:assignment_id>/picked-up', methods=['POST'])
@login_required
def mark_picked_up(assignment_id):
    volunteer = get_current_volunteer()
    if not volunteer:
        return redirect(url_for('main.home'))

    assignment = PickupAssignment.query.get_or_404(assignment_id)
    if assignment.volunteer_id != volunteer.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('volunteer.dashboard'))

    try:
        now = datetime.utcnow()
        assignment.status = 'picked_up'
        assignment.picked_up_at = now

        req = assignment.request
        if req and req.donation:
            mission = RescueMission.query.filter_by(donation_id=req.donation.id).first()
            if mission:
                MissionService.transition_state(mission, 'food_collected', current_user, "Food verified and collected by volunteer.")

        db.session.commit()
        flash('Food collection confirmed! Proceed to the destination NGO.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error confirming pickup: {str(e)}', 'danger')

    return redirect(url_for('volunteer.dashboard'))


@volunteer_bp.route('/pickup/<int:assignment_id>/delivered', methods=['POST'])
@login_required
def mark_delivered(assignment_id):
    volunteer = get_current_volunteer()
    if not volunteer:
        return redirect(url_for('main.home'))

    assignment = PickupAssignment.query.get_or_404(assignment_id)
    if assignment.volunteer_id != volunteer.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('volunteer.dashboard'))

    try:
        now = datetime.utcnow()
        assignment.status = 'delivered'
        assignment.delivered_at = now

        req = assignment.request
        if req and req.donation:
            mission = RescueMission.query.filter_by(donation_id=req.donation.id).first()
            if mission:
                MissionService.transition_state(mission, 'delivery_confirmed', current_user, "Delivered to destination NGO.")

        volunteer.available = True
        db.session.commit()
        flash('Delivery completed! Thank you for your service.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error confirming delivery: {str(e)}', 'danger')

    return redirect(url_for('volunteer.dashboard'))
