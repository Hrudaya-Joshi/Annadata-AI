from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models import FoodDonation, RescueMission, DonationRequest
from app.agents.food_analysis_agent import FoodAnalysisAgent
from app.agents.ngo_matching_agent import NGOMatchingAgent
from app.agents.coordination_agent import CoordinationAgent
from app.services.emergency_service import EmergencyRescueService
from app.tools.geo_tools import reverse_geocode, forward_geocode
from datetime import datetime

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/geo/reverse', methods=['GET', 'POST'])
def api_reverse_geocode():
    """Convert browser coordinates (lat, lon) to human-readable address."""
    if request.method == 'POST':
        data = request.get_json() or {}
        lat = data.get('latitude') or data.get('lat')
        lon = data.get('longitude') or data.get('lon') or data.get('lng')
    else:
        lat = request.args.get('lat') or request.args.get('latitude')
        lon = request.args.get('lon') or request.args.get('lng') or request.args.get('longitude')

    if lat is None or lon is None:
        return jsonify({"error": "Latitude and longitude required"}), 400

    try:
        address = reverse_geocode(lat, lon)
        return jsonify({
            "status": "success",
            "latitude": float(lat),
            "longitude": float(lon),
            "address": address
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@api_bp.route('/geo/forward', methods=['GET', 'POST'])
def api_forward_geocode():
    """Convert human-readable address to (latitude, longitude)."""
    if request.method == 'POST':
        data = request.get_json() or {}
        address = data.get('address') or ''
    else:
        address = request.args.get('address') or ''

    if not address.strip():
        return jsonify({"error": "Address string required"}), 400

    try:
        lat, lon = forward_geocode(address)
        return jsonify({
            "status": "success",
            "address": address,
            "latitude": lat,
            "longitude": lon
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@api_bp.route('/donate', methods=['POST'])
def donate():
    data = request.get_json() or {}
    required = [
        'restaurant_id', 'food_name', 'category', 'quantity', 'unit',
        'preparation_time', 'expiry_time', 'collection_deadline',
        'location_address', 'latitude', 'longitude'
    ]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field {field}"}), 400

    try:
        donation = FoodDonation(
            restaurant_id=int(data['restaurant_id']),
            food_name=data['food_name'],
            category=data['category'],
            quantity=int(data['quantity']),
            unit=data.get('unit', 'packets'),
            preparation_time=datetime.fromisoformat(data['preparation_time']),
            expiry_time=datetime.fromisoformat(data['expiry_time']),
            collection_deadline=datetime.fromisoformat(data['collection_deadline']),
            description=data.get('description', ''),
            location_address=data['location_address'],
            latitude=float(data['latitude']),
            longitude=float(data['longitude']),
            dietary_flags=data.get('dietary_flags'),
            packaging_type=data.get('packaging_type', 'Food-grade sealed containers')
        )
        db.session.add(donation)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

    analysis = FoodAnalysisAgent().run(donation.id)
    if not analysis.get('suitable'):
        return jsonify({
            "donation_id": donation.id,
            "rescue_code": donation.rescue_code,
            "status": "unsuitable",
            "analysis": analysis
        }), 200

    matching = NGOMatchingAgent().run(donation.id)
    return jsonify({
        "donation_id": donation.id,
        "rescue_code": donation.rescue_code,
        "status": "suitable",
        "analysis": analysis,
        "matching": matching
    }), 200


@api_bp.route('/analyze/<int:donation_id>', methods=['POST'])
def analyze(donation_id):
    return jsonify(FoodAnalysisAgent().run(donation_id))


@api_bp.route('/match/<int:donation_id>', methods=['POST'])
def match(donation_id):
    return jsonify(NGOMatchingAgent().run(donation_id))


@api_bp.route('/coordinate/<int:donation_id>', methods=['POST'])
def coordinate(donation_id):
    data = request.get_json() or {}
    ngo_id = data.get('ngo_id')
    volunteer_id = data.get('volunteer_id')
    return jsonify(CoordinationAgent().run(donation_id, ngo_id=ngo_id, volunteer_id=volunteer_id))


@api_bp.route('/emergencies', methods=['GET'])
def get_emergencies():
    alerts = EmergencyRescueService.scan_and_escalate(threshold_hours=2.0)
    return jsonify({
        "count": len(alerts),
        "emergencies": [
            {
                "donation_id": a["donation_id"],
                "food_name": a["food_name"],
                "mins_remaining": a["mins_remaining"],
                "badge": a["urgency_badge"]
            }
            for a in alerts
        ]
    })
