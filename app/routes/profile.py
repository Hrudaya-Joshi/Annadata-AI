from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.extensions import db
from app.models import AuditLog

profile_bp = Blueprint('profile', __name__, url_prefix='/profile')


@profile_bp.route('', methods=['GET', 'POST'])
@profile_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()

        if full_name:
            current_user.full_name = full_name
        current_user.phone = phone

        # Role specific updates
        lat = request.form.get('latitude')
        lng = request.form.get('longitude')

        if current_user.role == 'restaurant' and current_user.restaurant:
            b_name = request.form.get('business_name', '').strip()
            f_type = request.form.get('food_type', '').strip()
            addr = request.form.get('location_address', '').strip()
            if b_name:
                current_user.restaurant.business_name = b_name
            if f_type:
                current_user.restaurant.food_type = f_type
            if addr:
                current_user.restaurant.location_address = addr
            if lat and lng:
                try:
                    current_user.restaurant.latitude = float(lat)
                    current_user.restaurant.longitude = float(lng)
                except ValueError:
                    pass

        elif current_user.role == 'ngo' and current_user.ngo:
            org_name = request.form.get('organization_name', '').strip()
            cap = request.form.get('capacity_people')
            prefs = request.form.get('food_preferences', '').strip()
            addr = request.form.get('location_address', '').strip()
            if org_name:
                current_user.ngo.organization_name = org_name
            if cap:
                current_user.ngo.capacity_people = int(cap)
            if prefs:
                current_user.ngo.food_preferences = prefs
            if addr:
                current_user.ngo.location_address = addr
            if lat and lng:
                try:
                    current_user.ngo.latitude = float(lat)
                    current_user.ngo.longitude = float(lng)
                except ValueError:
                    pass

        elif current_user.role == 'volunteer' and current_user.volunteer:
            v_type = request.form.get('vehicle_type', '').strip()
            max_dist = request.form.get('max_distance_km')
            if v_type:
                current_user.volunteer.vehicle_type = v_type
            if max_dist:
                current_user.volunteer.max_distance_km = float(max_dist)
            if lat and lng:
                try:
                    current_user.volunteer.latitude = float(lat)
                    current_user.volunteer.longitude = float(lng)
                except ValueError:
                    pass

        audit = AuditLog(
            user_id=current_user.id,
            action="UPDATE_PROFILE",
            target_type="User",
            target_id=current_user.id,
            details="User updated profile information."
        )
        db.session.add(audit)
        db.session.commit()

        flash('Profile settings updated successfully!', 'success')
        return redirect(url_for('profile.index'))

    return render_template('profile/index.html')
