"""
Smart NGO Allocation Engine for ANNADATA AI
Calculates deterministic, explainable 100-point compatibility scores with fairness balancing.
"""
from datetime import datetime, timedelta
from app.extensions import db
from app.models import NGO, FoodDonation, DonationRequest, Volunteer, BeneficiaryDemand
from app.tools.geo_tools import calculate_distance_km


class AllocationEngine:
    """Deterministic Multi-Factor Scoring Engine for NGO Food Allocation."""

    @classmethod
    def evaluate_ngo(cls, donation: FoodDonation, ngo: NGO) -> dict:
        """
        Evaluate an NGO for a specific food donation.
        Returns a score (0 - 100) and a comprehensive component breakdown.
        """
        breakdown = {
            "distance_score": 0.0,
            "category_score": 0.0,
            "capacity_score": 0.0,
            "demand_score": 0.0,
            "volunteer_score": 0.0,
            "fairness_score": 0.0,
            "raw_distance_km": 0.0,
            "est_travel_time_mins": 0,
            "reasons": []
        }

        # 1. Distance & Estimated Travel Time (Max: 25 pts)
        try:
            distance = calculate_distance_km(
                donation.latitude, donation.longitude,
                ngo.latitude, ngo.longitude
            )
        except Exception:
            distance = 25.0

        breakdown["raw_distance_km"] = distance
        # Urban speed assumption: 20 km/h = 3 min/km + 8 min handling buffer
        est_mins = int(distance * 3 + 8)
        breakdown["est_travel_time_mins"] = est_mins

        if distance <= 2.0:
            dist_pts = 25.0
            breakdown["reasons"].append(f"Hyperlocal distance ({distance:.1f} km, ~{est_mins} mins)")
        elif distance <= 15.0:
            dist_pts = max(0.0, 25.0 * (1.0 - (distance - 2.0) / 13.0))
            breakdown["reasons"].append(f"Manageable transit distance ({distance:.1f} km, ~{est_mins} mins)")
        else:
            dist_pts = 0.0
            breakdown["reasons"].append(f"Exceeds priority distance radius ({distance:.1f} km)")

        breakdown["distance_score"] = round(dist_pts, 1)

        # 2. Category Compatibility (Max: 25 pts)
        ngo_prefs = [p.strip().lower() for p in (ngo.food_preferences or "").split(",") if p.strip()]
        don_cat = (donation.category or "").strip().lower()

        if don_cat in ngo_prefs or "all" in ngo_prefs or not ngo_prefs:
            cat_pts = 25.0
            breakdown["reasons"].append(f"Direct category match for '{donation.category}'")
        elif any(p in don_cat for p in ["veg", "meal", "grain"]) and "vegetarian" in ngo_prefs:
            cat_pts = 20.0
            breakdown["reasons"].append(f"Compatible dietary preference match for '{donation.category}'")
        else:
            cat_pts = 0.0
            breakdown["reasons"].append(f"Dietary preference mismatch ('{donation.category}' not in NGO preferences)")

        breakdown["category_score"] = cat_pts

        # 3. Capacity Compatibility (Max: 20 pts)
        quantity = donation.quantity or 1
        ngo_cap = ngo.capacity_people or 1

        if ngo_cap < quantity:
            cap_pts = 5.0  # Partial capacity
            breakdown["reasons"].append(f"NGO capacity ({ngo_cap}) is lower than donation quantity ({quantity})")
        else:
            ratio = quantity / ngo_cap
            if 0.2 <= ratio <= 1.0:
                cap_pts = 20.0
                breakdown["reasons"].append(f"Optimal capacity utilization ({int(ratio * 100)}% of {ngo_cap} people)")
            elif ratio > 0.05:
                cap_pts = 15.0
                breakdown["reasons"].append(f"Adequate capacity ({ngo_cap} people)")
            else:
                cap_pts = 10.0
                breakdown["reasons"].append(f"Large capacity NGO for relatively small batch ({quantity} vs {ngo_cap})")

        breakdown["capacity_score"] = cap_pts

        # 4. Beneficiary Demand & Urgency (Max: 15 pts)
        active_demand = BeneficiaryDemand.query.filter_by(
            ngo_id=ngo.id, status='active'
        ).first()

        demand_pts = 0.0
        if active_demand:
            if active_demand.category.lower() == don_cat:
                demand_pts += 10.0
                breakdown["reasons"].append("Active logged beneficiary demand for this exact category")
            else:
                demand_pts += 5.0
                breakdown["reasons"].append("Active general beneficiary demand")

            if active_demand.urgency_level in ['urgent', 'critical']:
                demand_pts += 5.0
                breakdown["reasons"].append("High urgency beneficiary priority flag")
        else:
            # Baseline demand score
            demand_pts = 5.0

        breakdown["demand_score"] = min(15.0, demand_pts)

        # 5. Volunteer Availability Proximity (Max: 5 pts)
        nearby_volunteers = Volunteer.query.filter_by(available=True).all()
        has_nearby = False
        for v in nearby_volunteers:
            try:
                v_dist = calculate_distance_km(v.latitude, v.longitude, donation.latitude, donation.longitude)
                if v_dist <= 8.0:
                    has_nearby = True
                    break
            except Exception:
                continue

        if has_nearby:
            vol_pts = 5.0
            breakdown["reasons"].append("Available rescue volunteers within 8 km radius")
        elif nearby_volunteers:
            vol_pts = 2.5
            breakdown["reasons"].append("Active volunteers available in wider metropolitan area")
        else:
            vol_pts = 0.0
            breakdown["reasons"].append("No active volunteer currently online in local sector")

        breakdown["volunteer_score"] = vol_pts

        # 6. Fair Allocation Mechanism (Max: 10 pts)
        # Prevents continuous monopolization by high-capacity NGOs
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_allocations = DonationRequest.query.filter(
            DonationRequest.ngo_id == ngo.id,
            DonationRequest.requested_at >= seven_days_ago
        ).count()

        if recent_allocations == 0:
            fair_pts = 10.0
            breakdown["reasons"].append("Fairness bonus: No recent allocations in past 7 days")
        elif recent_allocations <= 2:
            fair_pts = 8.0
            breakdown["reasons"].append(f"Fairness: Low recent allocation count ({recent_allocations} this week)")
        elif recent_allocations <= 5:
            fair_pts = 5.0
            breakdown["reasons"].append(f"Fairness: Moderate recent allocation count ({recent_allocations} this week)")
        else:
            fair_pts = 2.0
            breakdown["reasons"].append(f"Fairness load-balancing: High recent allocation count ({recent_allocations} this week)")

        breakdown["fairness_score"] = fair_pts

        # Total 100-pt Score
        total_score = (
            breakdown["distance_score"] +
            breakdown["category_score"] +
            breakdown["capacity_score"] +
            breakdown["demand_score"] +
            breakdown["volunteer_score"] +
            breakdown["fairness_score"]
        )
        total_score = round(min(100.0, max(0.0, total_score)), 1)
        breakdown["total_score"] = total_score

        # Structured explainability summary
        summary = (
            f"Overall Match: {total_score}/100. "
            f"Distance: {breakdown['distance_score']}/25 ({distance:.1f} km, ~{est_mins} mins transit). "
            f"Category Fit: {breakdown['category_score']}/25. "
            f"Capacity Fit: {breakdown['capacity_score']}/20. "
            f"Demand Priority: {breakdown['demand_score']}/15. "
            f"Volunteer Readiness: {breakdown['volunteer_score']}/5. "
            f"Fairness Balance: {breakdown['fairness_score']}/10."
        )
        breakdown["summary"] = summary
        return breakdown

    @classmethod
    def rank_ngos_for_donation(cls, donation: FoodDonation) -> list:
        """
        Rank all active verified NGOs for a food donation using the 100-pt algorithm.
        Returns sorted list of evaluated NGOs with full breakdown.
        """
        ngos = NGO.query.filter_by(is_active=True).all()
        ranked = []
        for ngo in ngos:
            eval_data = cls.evaluate_ngo(donation, ngo)
            ranked.append({
                "ngo": ngo,
                "ngo_id": ngo.id,
                "name": ngo.organization_name,
                "score": eval_data["total_score"],
                "breakdown": eval_data,
                "distance_km": eval_data["raw_distance_km"],
                "est_travel_time_mins": eval_data["est_travel_time_mins"],
                "eligible": eval_data["category_score"] > 0 and eval_data["total_score"] >= 30.0
            })

        ranked.sort(key=lambda x: x["score"], reverse=True)
        return ranked
