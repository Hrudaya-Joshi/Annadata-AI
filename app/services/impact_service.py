"""
AI Impact Intelligence & Analytics Service for ANNADATA AI
Calculates verified social and environmental impact strictly from delivered donations.
Separates Prepared Food (meals & kg), Fresh Produce (kg), and Raw Ingredients (kg)
into distinct, scientifically grounded metrics with transparent calculation methods.
"""
from datetime import datetime, timedelta
from sqlalchemy import func
from app.extensions import db
from app.models import (
    FoodDonation, RescueMission, ImpactRecord,
    Restaurant, NGO, Volunteer, User
)


class ImpactAnalyticsService:
    """Social and Environmental Impact Calculator with Transparent Categorical Separation."""

    # Documented benchmarks:
    # 1 kg edible food diverted from landfill = ~2.5 kg CO2e emissions avoided (UNEP / FAO benchmark)
    # 1 kg food produced = ~250 Liters of embedded freshwater conserved (Water Footprint Network)
    CO2_FACTOR_PER_KG = 2.5
    WATER_FACTOR_PER_KG = 250.0

    @classmethod
    def get_comprehensive_impact(cls) -> dict:
        """
        Aggregate verified platform impact data from the database.
        Strict rule: Only count delivered/completed rescue missions as verified impact.
        Never conflate individual meal portions with raw grain kilograms.
        """
        impact_records = ImpactRecord.query.all()

        # Categorical aggregations
        prepared_kg = 0.0
        prepared_meals = 0
        prepared_donations_count = 0

        produce_kg = 0.0
        produce_donations_count = 0

        raw_kg = 0.0
        raw_donations_count = 0

        delivered_ngos_set = set()

        for r in impact_records:
            d_cat = r.donation_category
            if not d_cat and r.donation_id:
                # Lazy-load donation to get category without requiring a relationship
                don = FoodDonation.query.get(r.donation_id)
                d_cat = (don.donation_category if don else None) or "prepared_food"
            d_cat = (d_cat or "prepared_food").lower()

            # Get ngo_id via mission join
            if r.mission_id:
                mission = RescueMission.query.get(r.mission_id)
                if mission and mission.ngo_id:
                    delivered_ngos_set.add(mission.ngo_id)

            if d_cat == "fresh_produce":
                produce_kg += r.quantity_kg
                produce_donations_count += 1
            elif d_cat == "raw_ingredients":
                raw_kg += r.quantity_kg
                raw_donations_count += 1
            else:
                prepared_kg += r.quantity_kg
                prepared_meals += r.meals_served
                prepared_donations_count += 1

        total_waste_prevented_kg = round(prepared_kg + produce_kg + raw_kg, 1)
        total_beneficiaries = sum(r.beneficiaries_reached for r in impact_records)
        total_co2_kg = round(total_waste_prevented_kg * cls.CO2_FACTOR_PER_KG, 1)
        total_water_liters = round(total_waste_prevented_kg * cls.WATER_FACTOR_PER_KG, 1)

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

        # 3 Major Categories Breakdown
        by_category = {
            "prepared_food": {
                "label": "Prepared Food & Cooked Meals",
                "meals_rescued": prepared_meals,
                "weight_kg": round(prepared_kg, 1),
                "successful_rescues": prepared_donations_count,
                "unit_display": f"{prepared_meals:,} Meals ({round(prepared_kg, 1):,} kg)"
            },
            "fresh_produce": {
                "label": "Fresh Produce (Fruits & Vegetables)",
                "weight_kg": round(produce_kg, 1),
                "successful_rescues": produce_donations_count,
                "unit_display": f"{round(produce_kg, 1):,} kg Produce"
            },
            "raw_ingredients": {
                "label": "Raw Ingredients & Food Staples",
                "weight_kg": round(raw_kg, 1),
                "successful_rescues": raw_donations_count,
                "unit_display": f"{round(raw_kg, 1):,} kg Staples"
            }
        }

        # Monthly trends (Past 6 months)
        month_labels = []
        monthly_rescued_kg = []
        monthly_donations_count = []

        now = datetime.utcnow()
        for i in range(5, -1, -1):
            m_start = datetime(now.year, now.month, 1) - timedelta(days=i * 30)
            m_label = m_start.strftime("%b %Y")
            month_labels.append(m_label)

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

        # NGO Leaderboard
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
                # Distinct category totals
                "prepared_meals_rescued": prepared_meals,
                "prepared_kg_rescued": round(prepared_kg, 1),
                "produce_kg_rescued": round(produce_kg, 1),
                "raw_ingredients_kg_rescued": round(raw_kg, 1),
                "total_waste_prevented_kg": total_waste_prevented_kg,
                "successful_donations": completed_missions,
                "ngos_served": len(delivered_ngos_set),
                "total_beneficiaries": total_beneficiaries,
                "total_co2_kg": total_co2_kg,
                "total_co2_tons": round(total_co2_kg / 1000.0, 3),
                "total_water_liters": total_water_liters,
                "total_water_kilo_liters": round(total_water_liters / 1000.0, 2),
            },
            "by_category": by_category,
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
                    "labels": ["Prepared Food", "Fresh Produce", "Raw Ingredients"],
                    "data": [round(prepared_kg, 1), round(produce_kg, 1), round(raw_kg, 1)],
                    "counts": [prepared_donations_count, produce_donations_count, raw_donations_count]
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
                "co2_ratio": "2.5 kg CO2e per kg food diverted from anaerobic landfill decomposition (FAO/UNEP benchmark).",
                "water_ratio": "250 L freshwater conservation per kg food embedded in agricultural and supply chains.",
                "transparency_note": "Prepared meals, fresh produce, and raw cooking staples are quantified with distinct units to prevent misleading metric inflation."
            }
        }
