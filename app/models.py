from datetime import datetime
from app.extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(20), nullable=False)  # 'restaurant', 'ngo', 'volunteer', 'admin'
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    restaurant = db.relationship('Restaurant', backref='user', uselist=False, cascade='all, delete-orphan')
    ngo = db.relationship('NGO', backref='user', uselist=False, cascade='all, delete-orphan')
    volunteer = db.relationship('Volunteer', backref='user', uselist=False, cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='recipient', lazy='dynamic', cascade='all, delete-orphan')
    audit_logs = db.relationship('AuditLog', backref='actor', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Restaurant(db.Model):
    __tablename__ = 'restaurants'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    business_name = db.Column(db.String(120), nullable=False)
    food_type = db.Column(db.String(100), nullable=True)
    location_address = db.Column(db.String(200), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    donations = db.relationship('FoodDonation', backref='restaurant', lazy='dynamic', cascade='all, delete-orphan')


class NGO(db.Model):
    __tablename__ = 'ngos'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    organization_name = db.Column(db.String(120), nullable=False)
    registration_number = db.Column(db.String(50), nullable=True)
    food_preferences = db.Column(db.String(200), nullable=True)
    accepted_categories = db.Column(db.String(200), default='prepared_food,fresh_produce,raw_ingredients')  # Supported donation categories
    storage_facilities = db.Column(db.String(200), default='dining_hall,cold_storage,dry_pantry')  # 'dry_pantry', 'cold_storage', 'dining_hall', 'freezer'
    capacity_people = db.Column(db.Integer, nullable=False, default=0)
    location_address = db.Column(db.String(200), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    requests = db.relationship('DonationRequest', backref='ngo', lazy='dynamic', cascade='all, delete-orphan')
    missions = db.relationship('RescueMission', backref='destination_ngo', lazy='dynamic')
    demands = db.relationship('BeneficiaryDemand', backref='requesting_ngo', lazy='dynamic', cascade='all, delete-orphan')


class Volunteer(db.Model):
    __tablename__ = 'volunteers'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    available = db.Column(db.Boolean, default=True)
    max_distance_km = db.Column(db.Float, default=10.0)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    vehicle_type = db.Column(db.String(50), default='bike')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    assignments = db.relationship('PickupAssignment', backref='volunteer', lazy='dynamic')
    missions = db.relationship('RescueMission', backref='courier_volunteer', lazy='dynamic')


class FoodDonation(db.Model):
    __tablename__ = 'food_donations'

    id = db.Column(db.Integer, primary_key=True)
    rescue_code = db.Column(db.String(36), unique=True, nullable=True, index=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    donation_category = db.Column(db.String(40), default='prepared_food', nullable=True)  # 'prepared_food', 'fresh_produce', 'raw_ingredients'
    food_name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # Subcategory / food type
    quantity = db.Column(db.Integer, nullable=False)
    unit = db.Column(db.String(20), nullable=False, default='packets')
    preparation_time = db.Column(db.DateTime, nullable=True)  # Prepared food: prep time; Produce: harvest/procure date
    expiry_time = db.Column(db.DateTime, nullable=False)  # Expiry or best-before
    collection_deadline = db.Column(db.DateTime, nullable=False)  # Available until
    description = db.Column(db.Text, nullable=True)
    location_address = db.Column(db.String(200), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(30), nullable=False, default='pending_analysis')
    suitability_score = db.Column(db.Float, nullable=True)
    analysis_report = db.Column(db.Text, nullable=True)
    is_emergency = db.Column(db.Boolean, default=False)
    storage_temperature = db.Column(db.String(50), nullable=True)
    dietary_flags = db.Column(db.String(100), nullable=True)
    packaging_type = db.Column(db.String(50), nullable=True)

    # Category-Specific Attributes
    produce_type = db.Column(db.String(80), nullable=True)  # e.g., 'Leafy Greens', 'Root Vegetables', 'Orchard Fruits'
    freshness_condition = db.Column(db.String(80), nullable=True)  # e.g., 'Freshly Harvested', 'Market Surplus', 'Ripe / Use Within 48h'
    harvest_date = db.Column(db.DateTime, nullable=True)
    ingredient_name = db.Column(db.String(120), nullable=True)  # e.g., 'Basmati Rice', 'Toor Dal', 'Wheat Flour'
    packaging_condition = db.Column(db.String(80), nullable=True)  # e.g., 'Factory Sealed', 'Bulk Jute Sack', 'Airtight Container'
    storage_requirements = db.Column(db.String(120), nullable=True)  # e.g., 'Dry Pantry', 'Moisture-Protected', 'Cool Aerated'
    image_url = db.Column(db.String(255), nullable=True)
    requires_human_verification = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    safety_assessment = db.relationship('FoodSafetyAssessment', backref='donation', uselist=False, cascade='all, delete-orphan')
    missions = db.relationship('RescueMission', backref='donation', lazy='dynamic', cascade='all, delete-orphan')


class FoodSafetyAssessment(db.Model):
    __tablename__ = 'food_safety_assessments'

    id = db.Column(db.Integer, primary_key=True)
    donation_id = db.Column(db.Integer, db.ForeignKey('food_donations.id'), unique=True, nullable=False)
    visual_inspection_passed = db.Column(db.Boolean, default=True)
    packaging_intact = db.Column(db.Boolean, default=True)
    temperature_controlled = db.Column(db.Boolean, default=True)
    allergens_declared = db.Column(db.Boolean, default=True)
    hygiene_verified = db.Column(db.Boolean, default=True)
    temperature_celsius = db.Column(db.Float, nullable=True)
    risk_level = db.Column(db.String(20), default='low')  # 'low', 'medium', 'high', 'critical'
    ai_risk_observations = db.Column(db.Text, nullable=True)
    requires_human_verification = db.Column(db.Boolean, default=False)
    category_checks = db.Column(db.Text, nullable=True)  # JSON-encoded category-specific checks
    safety_recommendations = db.Column(db.Text, nullable=True)
    verified_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    verified_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    verified_by = db.relationship('User', foreign_keys=[verified_by_user_id])


class DonationRequest(db.Model):
    __tablename__ = 'donation_requests'

    id = db.Column(db.Integer, primary_key=True)
    donation_id = db.Column(db.Integer, db.ForeignKey('food_donations.id'), nullable=False)
    ngo_id = db.Column(db.Integer, db.ForeignKey('ngos.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')  # 'pending', 'accepted', 'rejected'
    distance_km = db.Column(db.Float, nullable=True)
    match_score = db.Column(db.Float, nullable=True)
    score_breakdown = db.Column(db.Text, nullable=True)
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    responded_at = db.Column(db.DateTime, nullable=True)
    response_notes = db.Column(db.Text, nullable=True)

    donation = db.relationship('FoodDonation', foreign_keys=[donation_id], backref='donation_requests')
    pickup = db.relationship('PickupAssignment', backref='request', uselist=False, cascade='all, delete-orphan')


class PickupAssignment(db.Model):
    __tablename__ = 'pickup_assignments'

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('donation_requests.id'), nullable=False, unique=True)
    volunteer_id = db.Column(db.Integer, db.ForeignKey('volunteers.id'), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='assigned')  # 'assigned', 'accepted', 'picked_up', 'delivered', 'cancelled'
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    accepted_at = db.Column(db.DateTime, nullable=True)
    picked_up_at = db.Column(db.DateTime, nullable=True)
    delivered_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)


class RescueMission(db.Model):
    __tablename__ = 'rescue_missions'

    id = db.Column(db.Integer, primary_key=True)
    mission_code = db.Column(db.String(36), unique=True, nullable=False, index=True)
    donation_id = db.Column(db.Integer, db.ForeignKey('food_donations.id'), nullable=False)
    ngo_id = db.Column(db.Integer, db.ForeignKey('ngos.id'), nullable=False)
    volunteer_id = db.Column(db.Integer, db.ForeignKey('volunteers.id'), nullable=True)
    status = db.Column(db.String(30), nullable=False, default='submitted')
    # Valid statuses:
    # 1. 'submitted'
    # 2. 'safety_screening'
    # 3. 'ngo_matching'
    # 4. 'ngo_accepted'
    # 5. 'volunteer_assigned'
    # 6. 'pickup_initiated'
    # 7. 'food_collected'
    # 8. 'delivery_initiated'
    # 9. 'delivery_confirmed'
    # 10. 'completed'
    # Auxiliary: 'delayed', 'cancelled'

    pickup_deadline = db.Column(db.DateTime, nullable=True)
    delivery_deadline = db.Column(db.DateTime, nullable=True)
    pickup_time = db.Column(db.DateTime, nullable=True)
    delivery_time = db.Column(db.DateTime, nullable=True)
    verification_pin = db.Column(db.String(10), nullable=True)
    pickup_pin = db.Column(db.String(10), nullable=True)
    delivery_notes = db.Column(db.Text, nullable=True)
    cancellation_reason = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    impact = db.relationship('ImpactRecord', backref='mission', uselist=False, cascade='all, delete-orphan')


class BeneficiaryDemand(db.Model):
    __tablename__ = 'beneficiary_demands'

    id = db.Column(db.Integer, primary_key=True)
    ngo_id = db.Column(db.Integer, db.ForeignKey('ngos.id'), nullable=False)
    donation_category = db.Column(db.String(40), default='prepared_food', nullable=True)  # 'prepared_food', 'fresh_produce', 'raw_ingredients'
    category = db.Column(db.String(50), nullable=False)
    required_quantity = db.Column(db.Integer, nullable=False)
    unit = db.Column(db.String(20), default='meals')
    urgency_level = db.Column(db.String(20), default='normal')  # 'low', 'normal', 'urgent', 'critical'
    target_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='active')  # 'active', 'fulfilled', 'cancelled'
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(30), default='info')  # 'info', 'urgent', 'success', 'warning'
    link_url = db.Column(db.String(200), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    target_type = db.Column(db.String(50), nullable=True)
    target_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class DonationForecast(db.Model):
    __tablename__ = 'donation_forecasts'

    id = db.Column(db.Integer, primary_key=True)
    area_name = db.Column(db.String(100), nullable=False)
    day_of_week = db.Column(db.String(15), nullable=False)
    expected_quantity_kg = db.Column(db.Float, nullable=False)
    confidence_score = db.Column(db.Float, nullable=False)
    historical_sample_size = db.Column(db.Integer, default=0)
    is_demo_data = db.Column(db.Boolean, default=False)
    recommendations = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ImpactRecord(db.Model):
    __tablename__ = 'impact_records'

    id = db.Column(db.Integer, primary_key=True)
    mission_id = db.Column(db.Integer, db.ForeignKey('rescue_missions.id'), unique=True, nullable=False)
    donation_id = db.Column(db.Integer, db.ForeignKey('food_donations.id'), nullable=False)
    donation_category = db.Column(db.String(40), default='prepared_food', nullable=True)  # 'prepared_food', 'fresh_produce', 'raw_ingredients'
    quantity_kg = db.Column(db.Float, nullable=False)
    meals_served = db.Column(db.Integer, nullable=False)
    beneficiaries_reached = db.Column(db.Integer, nullable=False)
    co2_saved_kg = db.Column(db.Float, nullable=False)  # Est: 2.5 kg CO2e per kg food saved
    water_saved_liters = db.Column(db.Float, nullable=False)  # Est: 250 L per kg food saved
    verified_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AgentExecutionLog(db.Model):
    __tablename__ = 'agent_execution_logs'

    id = db.Column(db.Integer, primary_key=True)
    donation_id = db.Column(db.Integer, db.ForeignKey('food_donations.id'), nullable=True)
    agent_name = db.Column(db.String(50), nullable=False)
    task = db.Column(db.String(100), nullable=False)
    input_data = db.Column(db.Text, nullable=True)
    output_data = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='pending')
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
