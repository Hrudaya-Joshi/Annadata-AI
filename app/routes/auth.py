from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from app.extensions import db, login_manager
from app.models import User, Restaurant, NGO, Volunteer, AuditLog

auth_bp = Blueprint('auth', __name__)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ---------------- REGISTER ----------------

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return _redirect_role(current_user.role)

    if request.method == 'POST':
        role = request.form.get('role', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()

        if not email or not password or not full_name or not role:
            flash('All primary fields are required.', 'danger')
            return render_template('auth/register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('auth/register.html')

        if role not in ['restaurant', 'ngo', 'volunteer']:
            flash('Invalid role selected.', 'danger')
            return render_template('auth/register.html')

        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please login.', 'danger')
            return render_template('auth/register.html')

        try:
            user = User(
                role=role,
                email=email,
                full_name=full_name,
                phone=phone
            )
            user.set_password(password)
            db.session.add(user)
            db.session.flush()

            # Role-Specific Profiles
            if role == 'restaurant':
                b_name = request.form.get('business_name', '').strip() or full_name
                f_type = request.form.get('food_type', 'Multi-Cuisine')
                addr = request.form.get('location_address', 'Bengaluru, Karnataka')
                lat = float(request.form.get('latitude') or 12.9716)
                lon = float(request.form.get('longitude') or 77.5946)

                profile = Restaurant(
                    user_id=user.id,
                    business_name=b_name,
                    food_type=f_type,
                    location_address=addr,
                    latitude=lat,
                    longitude=lon
                )
                db.session.add(profile)

            elif role == 'ngo':
                org_name = request.form.get('organization_name', '').strip() or full_name
                reg_num = request.form.get('registration_number', 'NGO/REG/2026')
                prefs = request.form.get('food_preferences', 'vegetarian, cooked meals, fruits')
                cap = int(request.form.get('capacity_people') or 50)
                addr = request.form.get('location_address', 'Bengaluru, Karnataka')
                lat = float(request.form.get('latitude') or 12.9716)
                lon = float(request.form.get('longitude') or 77.5946)

                profile = NGO(
                    user_id=user.id,
                    organization_name=org_name,
                    registration_number=reg_num,
                    food_preferences=prefs,
                    capacity_people=cap,
                    location_address=addr,
                    latitude=lat,
                    longitude=lon,
                    is_active=True
                )
                db.session.add(profile)

            elif role == 'volunteer':
                dist = float(request.form.get('max_distance_km') or 10.0)
                vehicle = request.form.get('vehicle_type', 'bike')
                lat = float(request.form.get('latitude') or 12.9716)
                lon = float(request.form.get('longitude') or 77.5946)

                profile = Volunteer(
                    user_id=user.id,
                    available=True,
                    max_distance_km=dist,
                    vehicle_type=vehicle,
                    latitude=lat,
                    longitude=lon
                )
                db.session.add(profile)

            audit = AuditLog(
                user_id=user.id,
                action="REGISTER",
                target_type="User",
                target_id=user.id,
                details=f"User registered with role {role} ({email})"
            )
            db.session.add(audit)

            db.session.commit()
            flash('Registration successful! Please sign in with your credentials.', 'success')
            return redirect(url_for('auth.login'))

        except (ValueError, TypeError) as e:
            db.session.rollback()
            flash(f'Invalid form inputs: {str(e)}', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Registration error: {str(e)}', 'danger')

    return render_template('auth/register.html')


# ---------------- LOGIN ----------------

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return _redirect_role(current_user.role)

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            if not user.is_active:
                flash('This account has been deactivated. Please contact support.', 'danger')
                return render_template('auth/login.html')

            login_user(user)

            # Audit login
            audit = AuditLog(
                user_id=user.id,
                action="LOGIN",
                target_type="User",
                target_id=user.id,
                details=f"Successful login for {user.email}"
            )
            db.session.add(audit)
            db.session.commit()

            flash(f'Welcome back, {user.full_name}!', 'success')
            return _redirect_role(user.role)
        else:
            flash('Invalid email or password. Please try again.', 'danger')

    return render_template('auth/login.html')


# ---------------- LOGOUT ----------------

@auth_bp.route('/logout')
def logout():
    if current_user.is_authenticated:
        audit = AuditLog(
            user_id=current_user.id,
            action="LOGOUT",
            target_type="User",
            target_id=current_user.id,
            details=f"User {current_user.email} signed out."
        )
        db.session.add(audit)
        db.session.commit()
        logout_user()

    flash('You have been securely signed out.', 'info')
    return redirect(url_for('main.home'))


def _redirect_role(role: str):
    if role == 'restaurant':
        return redirect(url_for('restaurant.dashboard'))
    elif role == 'ngo':
        return redirect(url_for('ngo.dashboard'))
    elif role == 'volunteer':
        return redirect(url_for('volunteer.dashboard'))
    elif role == 'admin':
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('main.home'))
