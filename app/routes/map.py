from flask import Blueprint, render_template, jsonify
from flask_login import current_user
from app.models import FoodDonation, NGO, Volunteer, RescueMission

map_bp = Blueprint('map', __name__)


@map_bp.route('/map')
def view_map():
    return render_template('map/index.html')


@map_bp.route('/api/map/data')
def get_map_data():
    """Return geospatial markers filtered according to user permissions."""
    is_authenticated = current_user.is_authenticated

    # 1. Active Donations
    active_donations = FoodDonation.query.filter(
        FoodDonation.status.in_(['suitable', 'matched', 'pending_matching', 'requested'])
    ).all()

    donation_markers = []
    for d in active_donations:
        donation_markers.append({
            "id": d.id,
            "type": "donation",
            "name": d.food_name,
            "category": d.category,
            "quantity": f"{d.quantity} {d.unit}",
            "lat": d.latitude,
            "lng": d.longitude,
            "is_emergency": d.is_emergency,
            "address": d.location_address if is_authenticated else d.location_address.split(",")[-1].strip(),
            "deadline": d.collection_deadline.strftime("%H:%M UTC") if d.collection_deadline else None,
            "passport_url": f"/passport/{d.rescue_code or d.id}"
        })

    # 2. Verified NGOs
    ngos = NGO.query.filter_by(is_active=True).all()
    ngo_markers = []
    for ngo in ngos:
        ngo_markers.append({
            "id": ngo.id,
            "type": "ngo",
            "name": ngo.organization_name,
            "capacity": ngo.capacity_people,
            "lat": ngo.latitude,
            "lng": ngo.longitude,
            "address": ngo.location_address if is_authenticated else ngo.location_address.split(",")[-1].strip()
        })

    # 3. Available Volunteers (Only approximate sector for safety, and only to authenticated users)
    volunteer_markers = []
    if is_authenticated:
        vols = Volunteer.query.filter_by(available=True).all()
        for v in vols:
            volunteer_markers.append({
                "id": v.id,
                "type": "volunteer",
                "name": f"Volunteer #{v.id} ({v.vehicle_type or 'Bike'})",
                "lat": v.latitude,
                "lng": v.longitude,
                "available": v.available
            })

    # 4. Active Transit Routes (Missions in transit)
    transit_routes = []
    in_transit_missions = RescueMission.query.filter(
        RescueMission.status.in_(['pickup_initiated', 'food_collected', 'delivery_initiated'])
    ).all()
    for m in in_transit_missions:
        if m.donation and m.destination_ngo:
            transit_routes.append({
                "mission_code": m.mission_code,
                "status": m.status,
                "from_lat": m.donation.latitude,
                "from_lng": m.donation.longitude,
                "to_lat": m.destination_ngo.latitude,
                "to_lng": m.destination_ngo.longitude,
                "food": m.donation.food_name
            })

    return jsonify({
        "donations": donation_markers,
        "ngos": ngo_markers,
        "volunteers": volunteer_markers,
        "transit_routes": transit_routes
    })
