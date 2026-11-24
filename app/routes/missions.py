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

    # PIN wale status sirf dedicated verification routes se badlenge.
    if new_status in ['food_collected', 'delivery_confirmed']:
        flash('Is kaam ke liye PIN verification zaroori hai.', 'danger')
        return redirect(url_for('missions.mission_detail', mission_id=mission.id))

    authorized = False

    if current_user.role == 'admin':
        authorized = True

    elif current_user.role == 'volunteer':
        volunteer = current_user.volunteer
        if volunteer and mission.volunteer_id == volunteer.id:
            if new_status in ['pickup_initiated', 'delivery_initiated']:
                authorized = True

    elif current_user.role == 'ngo':
        ngo = current_user.ngo
        if ngo and mission.ngo_id == ngo.id:
            if new_status in ['completed', 'cancelled']:
                authorized = True

    elif current_user.role == 'restaurant':
        restaurant = current_user.restaurant
        if restaurant and mission.donation and mission.donation.restaurant_id == restaurant.id:
            if new_status == 'cancelled':
                authorized = True

    if not authorized:
        flash('You are not authorized to make this change.', 'danger')
        return redirect(url_for('missions.mission_detail', mission_id=mission.id))

    success, msg = MissionService.transition_state(
        mission, new_status, current_user, notes
    )

    flash(msg, 'success' if success else 'danger')
    return redirect(url_for('missions.mission_detail', mission_id=mission.id))


@missions_bp.route('/mission/<int:mission_id>/verify-pickup', methods=['POST'])
@login_required
def verify_pickup_pin(mission_id):
    mission = RescueMission.query.get_or_404(mission_id)

    volunteer = current_user.volunteer if current_user.role == 'volunteer' else None

    if not volunteer or mission.volunteer_id != volunteer.id:
        flash('Sirf assigned volunteer PIN verify kar sakta hai.', 'danger')
        return redirect(url_for('missions.mission_detail', mission_id=mission.id))

    if mission.status != 'pickup_initiated':
        flash('Pickup PIN is stage par verify nahi ho sakta.', 'danger')
        return redirect(url_for('missions.mission_detail', mission_id=mission.id))

    pin_entered = request.form.get('pin', '').strip()

    success, msg = MissionService.transition_state(
        mission,
        'food_collected',
        current_user,
        'Kitchen Collection PIN verified.',
        pin=pin_entered
    )

    flash(msg, 'success' if success else 'danger')
    return redirect(url_for('missions.mission_detail', mission_id=mission.id))


@missions_bp.route('/mission/<int:mission_id>/verify-delivery', methods=['POST'])
@login_required
def verify_delivery_pin(mission_id):
    mission = RescueMission.query.get_or_404(mission_id)

    volunteer = current_user.volunteer if current_user.role == 'volunteer' else None

    if not volunteer or mission.volunteer_id != volunteer.id:
        flash('Sirf assigned volunteer PIN verify kar sakta hai.', 'danger')
        return redirect(url_for('missions.mission_detail', mission_id=mission.id))

    if mission.status != 'delivery_initiated':
        flash('Delivery PIN is stage par verify nahi ho sakta.', 'danger')
        return redirect(url_for('missions.mission_detail', mission_id=mission.id))

    pin_entered = request.form.get('pin', '').strip()
    notes = request.form.get('notes', '').strip()

    success, msg = MissionService.transition_state(
        mission,
        'delivery_confirmed',
        current_user,
        f'Shelter Delivery PIN verified. Notes: {notes}',
        pin=pin_entered
    )

    flash(msg, 'success' if success else 'danger')
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
