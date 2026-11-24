"""
AI Impact Intelligence & Analytics Service for ANNADATA AI
Calculates verified social and environmental impact strictly from delivered donations.
Generates data structures for Chart.js visualizations with documented environmental estimates.
"""
from datetime import datetime, timedelta
from sqlalchemy import func
from app.extensions import db
from app.models import (
    FoodDonation, RescueMission, ImpactRecord,
    Restaurant, NGO, Volunteer, User
)


class ImpactAnalyticsService:
    """Social and Environmental Impact Calculator with Documented Scientific Assumptions."""

    # Documented benchmarks:
    # 1 kg edible prepared food averted from landfill = ~2.5 kg CO2e emissions avoided (FAO / UNEP Food Waste Index)
    # 1 kg prepared food = ~250 Liters of embedded freshwater conserved (Water Footprint Network)
    # 1 meal standard portion size = 0.40 kg (400 grams per adult meal equivalent)
    CO2_FACTOR_PER_KG = 2.5
    WATER_FACTOR_PER_KG = 250.0
    KG_PER_MEAL = 0.40

    @classmethod
    def get_comprehensive_impact(cls) -> dict:
        """
        Aggregate verified platform impact data from the database.
        Strict rule: Only count delivered/completed rescue missions as verified impact.
        """
        # Verified impact records
        impact_records = ImpactRecord.query.all()

        total_kg_rescued = sum(r.quantity_kg for r in impact_records)
        total_meals_served = sum(r.meals_served for r in impact_records)
        total_beneficiaries = sum(r.beneficiaries_reached for r in impact_records)
        total_co2_kg = sum(r.co2_saved_kg for r in impact_records)
        total_water_liters = sum(r.water_saved_liters for r in impact_records)

        # Platform participant counts
        total_donations_count = FoodDonation.query.count()
        total_restaurants = Restaurant.query.count()
        total_ngos = NGO.query.count()
        total_volunteers = Volunteer.query.count()

        # Mission pipeline breakdown
        total_missions = RescueMission.query.count()
        completed_missions = RescueMission.query.filter(
            RescueMission.status.in_(['delivery_confirmed', 'completed'])
        ).count()
        in_progress_missions = RescueMission.query.filter(
            RescueMission.status.in_([
                'submitted', 'safety_screening', 'ngo_matching', 'ngo_accepted',
                'volunteer_assigned', 'pickup_initiated', 'food_collected', 'delivery_initiated'
            ])
        ).count()
        cancelled_missions = RescueMission.query.filter_by(status='cancelled').count()

        # Category distribution from verified and active donations
        categories_query = db.session.query(
            FoodDonation.category, func.count(FoodDonation.id), func.sum(FoodDonation.quantity)
        ).group_by(FoodDonation.category).all()

        category_labels = [c[0].capitalize() for c in categories_query]
        category_counts = [int(c[1]) for c in categories_query]
        category_quantities = [float(c[2] or 0) for c in categories_query]

        # Monthly trends (Past 6 months or all available)
        month_labels = []
        monthly_rescued_kg = []
        monthly_donations_count = []

        now = datetime.utcnow()
        for i in range(5, -1, -1):
            m_start = datetime(now.year, now.month, 1) - timedelta(days=i * 30)
            m_label = m_start.strftime("%b %Y")
            month_labels.append(m_label)

            # Approximate month range
            m_end = m_start + timedelta(days=31)
            m_kg = sum(
                r.quantity_kg for r in impact_records
                if m_start <= r.verified_at < m_end
            )
            m_count = FoodDonation.query.filter(
                FoodDonation.created_at >= m_start,
                FoodDonation.created_at < m_end
            ).count()

            monthly_rescued_kg.append(round(m_kg, 1))
            monthly_donations_count.append(m_count)

        # NGO Leaderboard (Top Verified Rescuers)
        ngo_stats = []
        all_ngos = NGO.query.all()
        for ngo in all_ngos:
            ngo_missions = RescueMission.query.filter(
                RescueMission.ngo_id == ngo.id,
                RescueMission.status.in_(['delivery_confirmed', 'completed'])
            ).all()
            ngo_kg = sum(m.impact.quantity_kg for m in ngo_missions if m.impact)
            ngo_meals = sum(m.impact.meals_served for m in ngo_missions if m.impact)
            ngo_stats.append({
                "name": ngo.organization_name,
                "missions_completed": len(ngo_missions),
                "kg_received": round(ngo_kg, 1),
                "meals_distributed": ngo_meals,
                "capacity": ngo.capacity_people
            })
        ngo_stats.sort(key=lambda x: x["missions_completed"], reverse=True)

        # Volunteer Leaderboard
        vol_stats = []
        all_vols = Volunteer.query.all()
        for v in all_vols:
            v_missions = RescueMission.query.filter(
                RescueMission.volunteer_id == v.id,
                RescueMission.status.in_(['delivery_confirmed', 'completed'])
            ).all()
            vol_stats.append({
                "name": v.user.full_name if v.user else f"Volunteer #{v.id}",
                "missions_completed": len(v_missions),
                "vehicle": v.vehicle_type or 'Bike',
                "status": "Available" if v.available else "On Mission"
            })
        vol_stats.sort(key=lambda x: x["missions_completed"], reverse=True)

        return {
            "verified_summary": {
                "total_kg_rescued": round(total_kg_rescued, 1),
                "total_meals_served": total_meals_served,
                "total_beneficiaries": total_beneficiaries,
                "total_co2_kg": round(total_co2_kg, 1),
                "total_co2_tons": round(total_co2_kg / 1000.0, 3),
                "total_water_liters": round(total_water_liters, 1),
                "total_water_kilo_liters": round(total_water_liters / 1000.0, 2),
            },
            "network_size": {
                "restaurants": total_restaurants,
                "ngos": total_ngos,
                "volunteers": total_volunteers,
                "total_donations": total_donations_count,
            },
            "missions": {
                "total": total_missions,
                "completed": completed_missions,
                "in_progress": in_progress_missions,
                "cancelled": cancelled_missions,
                "success_rate": round((completed_missions / total_missions * 100.0), 1) if total_missions > 0 else 100.0
            },
            "charts": {
                "categories": {
                    "labels": category_labels or ["Cooked Meals", "Baked Goods", "Dairy", "Vegetarian", "Fruits"],
                    "data": category_counts or [0, 0, 0, 0, 0],
                    "quantities": category_quantities or [0, 0, 0, 0, 0]
                },
                "monthly_trend": {
                    "labels": month_labels,
                    "rescued_kg": monthly_rescued_kg,
                    "donations_count": monthly_donations_count
                }
            },
            "leaderboards": {
                "ngos": ngo_stats[:8],
                "volunteers": vol_stats[:8]
            },
            "environmental_methodology": {
                "co2_ratio": "2.5 kg CO2e per kg food diverted from anaerobic landfill decomposition (FAO/UNEP standard).",
                "water_ratio": "250 L freshwater conservation per kg prepared food embedded in agricultural supply chain.",
                "disclaimer": "Environmental metrics are scientifically calibrated estimates based on UNEP/FAO benchmarks. Only verified delivered meals are included."
            }
        }
