from flask import Blueprint, render_template
from app.models import FoodDonation, RescueMission, NGO, Restaurant, Volunteer, ImpactRecord
from app.services.impact_service import ImpactAnalyticsService

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def home():
    impact_data = ImpactAnalyticsService.get_comprehensive_impact()

    # Recent verified deliveries
    recent_missions = RescueMission.query.filter(
        RescueMission.status.in_(['delivery_confirmed', 'completed'])
    ).order_by(RescueMission.delivery_time.desc()).limit(3).all()

    # Active network stats
    donor_count = Restaurant.query.count()
    ngo_count = NGO.query.count()
    volunteer_count = Volunteer.query.count()

    return render_template(
        'home.html',
        impact=impact_data,
        recent_missions=recent_missions,
        donor_count=donor_count,
        ngo_count=ngo_count,
        volunteer_count=volunteer_count
    )
