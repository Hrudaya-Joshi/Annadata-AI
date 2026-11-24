from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models import RescueMission, Volunteer, AuditLog
from app.services.mission_service import MissionService

missions_bp = Blueprint('missions', __name__)


@missions_bp.route('/missions')
@login_required
def list_missions():
    status_filter = request.args.get('status')

    query = RescueMission.query

    # Role-based scoping
    if current_user.role == 'restaurant':
        rest = current_user.restaurant
        if not rest:
            flash('Restaurant profile not found.', 'danger')
            return redirect(url_for('main.home'))
        query = query.join(RescueMission.donation).filter_by(restaurant_id=rest.id)

    elif current_user.role == 'ngo':
        ngo = current_user.ngo
        if not ngo:
            flash('NGO profile not found.', 'danger')
            return redirect(url_for('main.home'))
        query = query.filter_by(ngo_id=ngo.id)

    elif current_user.role == 'volunteer':
        vol = current_user.volunteer
        if not vol:
            flash('Volunteer profile not found.', 'danger')
            return redirect(url_for('main.home'))
        query = query.filter_by(volunteer_id=vol.id)

    # Status filter
    if status_filter == 'active':
        query = query.filter(RescueMission.status.notin_(['completed', 'cancelled']))
    elif status_filter == 'completed':
        query = query.filter(RescueMission.status.in_(['delivery_confirmed', 'completed']))
    elif status_filter == 'delayed':
        query = query.filter_by(status='delayed')

    missions = query.order_by(RescueMission.updated_at.desc()).all()
    return render_template('missions/index.html', missions=missions, current_filter=status_filter)


@missions_bp.route('/mission/<int:mission_id>')
@login_required
def mission_detail(mission_id):
    mission = RescueMission.query.get_or_404(mission_id)

    # Ownership / authorization check
    is_owner = (
        current_user.role == 'admin' or
        (current_user.restaurant and mission.donation and current_user.restaurant.id == mission.donation.restaurant_id) or
        (current_user.ngo and current_user.ngo.id == mission.ngo_id) or
        (current_user.volunteer and current_user.volunteer.id == mission.volunteer_id)
    )
    if not is_owner:
        flash('Access denied: You do not have permission to view this mission.', 'danger')
        return redirect(url_for('main.home'))

    # Available volunteers for admin / NGO reassignment
    available_volunteers = Volunteer.query.filter_by(available=True).all() if current_user.role in ['admin', 'ngo'] else []

    allowed_next_states = MissionService.VALID_TRANSITIONS.get(mission.status, [])

    return render_template(
        'missions/detail.html',
        mission=mission,
        allowed_next_states=allowed_next_states,
        available_volunteers=available_volunteers,
        status_display=MissionService.STATUS_DISPLAY
    )


@missions_bp.route('/mission/<int:mission_id>/transition', methods=['POST'])
@login_required
def transition_mission(mission_id):
    mission = RescueMission.query.get_or_404(mission_id)
    new_status = request.form.get('new_status', '').strip()
    notes = request.form.get('notes', '').strip()

    # Role permission checks on state changes
    # Volunteers can trigger: pickup_initiated, food_collected, delivery_initiated
    # NGOs can trigger: delivery_confirmed, completed
    # Admins can trigger any valid transition
    authorized = False
    if current_user.role == 'admin':
        authorized = True
    elif current_user.role == 'volunteer' and mission.volunteer_id == current_user.volunteer.id:
        if new_status in ['pickup_initiated', 'food_collected', 'delivery_initiated']:
            authorized = True
    elif current_user.role == 'ngo' and mission.ngo_id == current_user.ngo.id:
        if new_status in ['delivery_confirmed', 'completed', 'cancelled']:
            authorized = True
    elif current_user.role == 'restaurant' and mission.donation and mission.donation.restaurant_id == current_user.restaurant.id:
        if new_status == 'cancelled':
            authorized = True

    if not authorized:
        flash('You are not authorized to transition this mission to the selected state.', 'danger')
        return redirect(url_for('missions.mission_detail', mission_id=mission.id))

    success, msg = MissionService.transition_state(mission, new_status, current_user, notes)
    if success:
        flash(msg, 'success')
    else:
        flash(msg, 'danger')

    return redirect(url_for('missions.mission_detail', mission_id=mission.id))


@missions_bp.route('/mission/<int:mission_id>/verify-delivery', methods=['POST'])
@login_required
def verify_delivery_pin(mission_id):
    mission = RescueMission.query.get_or_404(mission_id)

    if current_user.role not in ['ngo', 'admin']:
        flash('Only destination NGO or administrators can verify delivery.', 'danger')
        return redirect(url_for('missions.mission_detail', mission_id=mission.id))

    pin_entered = request.form.get('pin', '').strip()
    notes = request.form.get('notes', '').strip()

    if not mission.verification_pin or pin_entered == mission.verification_pin or current_user.role == 'admin':
        success, msg = MissionService.transition_state(mission, 'delivery_confirmed', current_user, f"PIN Verified. Notes: {notes}")
        if success:
            flash('Delivery successfully verified and impact confirmed!', 'success')
        else:
            flash(msg, 'danger')
    else:
        flash('Invalid verification PIN. Please request the PIN from the volunteer courier.', 'danger')

    return redirect(url_for('missions.mission_detail', mission_id=mission.id))


@missions_bp.route('/mission/<int:mission_id>/assign-volunteer', methods=['POST'])
@login_required
def assign_volunteer(mission_id):
    mission = RescueMission.query.get_or_404(mission_id)

    if current_user.role not in ['admin', 'ngo']:
        flash('Unauthorized to assign volunteers.', 'danger')
        return redirect(url_for('missions.mission_detail', mission_id=mission.id))

    volunteer_id = request.form.get('volunteer_id')
    if not volunteer_id:
        flash('Please select a volunteer.', 'warning')
        return redirect(url_for('missions.mission_detail', mission_id=mission.id))

    vol = Volunteer.query.get_or_404(int(volunteer_id))
    mission.volunteer_id = vol.id
    vol.available = False
    if mission.status == 'ngo_accepted':
        mission.status = 'volunteer_assigned'

    audit = AuditLog(
        user_id=current_user.id,
        action="ASSIGN_VOLUNTEER",
        target_type="RescueMission",
        target_id=mission.id,
        details=f"Assigned volunteer #{vol.id} to mission {mission.mission_code}"
    )
    db.session.add(audit)
    db.session.commit()

    flash(f'Volunteer assigned successfully to mission {mission.mission_code}.', 'success')
    return redirect(url_for('missions.mission_detail', mission_id=mission.id))
