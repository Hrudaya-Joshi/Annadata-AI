from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Restaurant, FoodDonation, DonationRequest, RescueMission
from app.agents.food_analysis_agent import FoodAnalysisAgent
from app.agents.ngo_matching_agent import NGOMatchingAgent
from app.services.forecast_service import SurplusForecastingService

restaurant_bp = Blueprint(
    'restaurant',
    __name__,
    url_prefix='/restaurant'
)


def get_current_restaurant():
    if current_user.role != 'restaurant':
        flash('Access denied.', 'danger')
        return None
    rest = Restaurant.query.filter_by(user_id=current_user.id).first()
    if not rest:
        flash('Restaurant profile not found.', 'danger')
    return rest


@restaurant_bp.route('/dashboard')
@login_required
def dashboard():
    restaurant = get_current_restaurant()
    if not restaurant:
        return redirect(url_for('main.home'))

    donations = FoodDonation.query.filter_by(
        restaurant_id=restaurant.id
    ).order_by(
        FoodDonation.created_at.desc()
    ).all()

    # Donation statistics
    total_donations = len(donations)
    successful_rescues = len([d for d in donations if d.status in ['delivered', 'completed']])
    pending_donations = len([d for d in donations if d.status in ['pending_analysis', 'suitable', 'matched', 'requested']])
    total_kg = sum(d.quantity * (0.45 if d.unit != 'kg' else 1.0) for d in donations if d.status in ['delivered', 'completed'])

    # AI Surplus Predictions for this restaurant/area
    forecasting = SurplusForecastingService.get_intelligence_overview()

    # Active requests status lookup
    donation_ids = [d.id for d in donations]
    request_statuses = {}
    if donation_ids:
        reqs = DonationRequest.query.filter(DonationRequest.donation_id.in_(donation_ids)).all()
        for r in reqs:
            if r.donation_id not in request_statuses or r.status == 'accepted':
                request_statuses[r.donation_id] = r.status

    return render_template(
        'restaurant/dashboard.html',
        restaurant=restaurant,
        donations=donations[:10],
        total_donations=total_donations,
        successful_rescues=successful_rescues,
        pending_donations=pending_donations,
        total_kg=round(total_kg, 1),
        forecast=forecasting,
        request_statuses=request_statuses
    )


@restaurant_bp.route('/donate', methods=['GET', 'POST'])
@login_required
def donate():
    restaurant = get_current_restaurant()
    if not restaurant:
        return redirect(url_for('main.home'))

    if request.method == 'POST':
        try:
            food_name = request.form.get('food_name', '').strip()
            category = request.form.get('category', '').strip()
            quantity = int(request.form.get('quantity', 0))
            unit = request.form.get('unit', 'packets')
            prep_str = request.form.get('preparation_time')
            exp_str = request.form.get('expiry_time')
            dead_str = request.form.get('collection_deadline')
            description = request.form.get('description', '').strip()
            dietary_flags = request.form.get('dietary_flags', '').strip()
            storage_temp = request.form.get('storage_temperature', 'Room Temperature')
            packaging_type = request.form.get('packaging_type', 'Food-grade containers')

            # Validation
            if not food_name or not category:
                raise ValueError('Food name and category are required.')
            if quantity <= 0:
                raise ValueError('Quantity must be greater than zero.')
            if not all([prep_str, exp_str, dead_str]):
                raise ValueError('Please complete all date and time fields.')

            preparation_time = datetime.fromisoformat(prep_str)
            expiry_time = datetime.fromisoformat(exp_str)
            collection_deadline = datetime.fromisoformat(dead_str)

            if expiry_time <= preparation_time:
                raise ValueError('Expiry time must be chronologically after preparation time.')
            if collection_deadline <= preparation_time:
                raise ValueError('Collection deadline must be after preparation time.')
            if collection_deadline > expiry_time:
                raise ValueError('Collection deadline cannot exceed food expiry time.')

            # Safety checklist items from form
            checklist = {
                'visual_inspection_passed': request.form.get('check_visual') == 'on',
                'packaging_intact': request.form.get('check_packaging') == 'on',
                'temperature_controlled': request.form.get('check_temp') == 'on',
                'allergens_declared': request.form.get('check_allergens') == 'on',
                'hygiene_verified': request.form.get('check_hygiene') == 'on',
                'temperature_celsius': float(request.form.get('temperature_celsius') or (4.0 if category == 'dairy' else 65.0))
            }

            # Create FoodDonation
            donation = FoodDonation(
                restaurant_id=restaurant.id,
                food_name=food_name,
                category=category,
                quantity=quantity,
                unit=unit,
                preparation_time=preparation_time,
                expiry_time=expiry_time,
                collection_deadline=collection_deadline,
                description=description,
                dietary_flags=dietary_flags,
                storage_temperature=storage_temp,
                packaging_type=packaging_type,
                location_address=request.form.get('location_address') or restaurant.location_address,
                latitude=float(request.form.get('latitude') or restaurant.latitude),
                longitude=float(request.form.get('longitude') or restaurant.longitude),
                status='pending_analysis'
            )
            db.session.add(donation)
            db.session.commit()

            # Execute Food Analysis Agent with safety checklist
            analysis = FoodAnalysisAgent().run(donation.id, safety_checklist=checklist)

            if not analysis or not analysis.get('suitable'):
                flash('Food donation registered but flagged by Safety Screening. Please review safety details.', 'warning')
                return redirect(url_for('restaurant.donation_detail', donation_id=donation.id))

            # Automatically execute Smart NGO Allocation Engine
            matching = NGOMatchingAgent().run(donation.id)
            if matching and matching.get('eligible'):
                flash(f'Success! Food Rescue Passport generated ({donation.rescue_code}) and matched with eligible NGOs.', 'success')
            else:
                flash(f'Donation verified safe ({donation.rescue_code}). In queue for NGO matching.', 'info')

            return redirect(url_for('restaurant.donation_detail', donation_id=donation.id))

        except (ValueError, TypeError) as e:
            db.session.rollback()
            flash(f'Validation Error: {str(e)}', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Error processing donation: {str(e)}', 'danger')

    return render_template('restaurant/donate.html', restaurant=restaurant)


@restaurant_bp.route('/donations')
@login_required
def donations():
    restaurant = get_current_restaurant()
    if not restaurant:
        return redirect(url_for('main.home'))

    all_donations = FoodDonation.query.filter_by(
        restaurant_id=restaurant.id
    ).order_by(
        FoodDonation.created_at.desc()
    ).all()

    return render_template(
        'restaurant/donations.html',
        restaurant=restaurant,
        donations=all_donations
    )


@restaurant_bp.route('/donation/<int:donation_id>')
@login_required
def donation_detail(donation_id):
    restaurant = get_current_restaurant()
    if not restaurant:
        return redirect(url_for('main.home'))

    donation = FoodDonation.query.get_or_404(donation_id)
    if donation.restaurant_id != restaurant.id and current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('restaurant.dashboard'))

    requests = DonationRequest.query.filter_by(donation_id=donation.id).all()
    mission = RescueMission.query.filter_by(donation_id=donation.id).first()

    return render_template(
        'restaurant/donation_detail.html',
        donation=donation,
        requests=requests,
        mission=mission,
        safety=donation.safety_assessment
    )
