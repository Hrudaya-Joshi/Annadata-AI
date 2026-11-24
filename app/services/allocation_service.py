"""
Smart NGO Allocation Engine for ANNADATA AI
Calculates deterministic, explainable 100-point compatibility scores across
Prepared Food, Fresh Produce, and Raw Food Ingredients.

Enforces:
1. Category & Active Demand Matching (e.g. an NGO requesting raw rice will NOT
   be matched with prepared hot meals merely due to close proximity).
2. Storage Facility Alignment (cold storage vs dry warehouse vs dining hall).
3. Realistic Category Transit Urgency (tight radius for hot meals, wider for grains).
4. Capacity & Load Balancing (anti-hoarding fairness mechanism).
"""
from datetime import datetime, timedelta
from app.extensions import db
from app.models import NGO, FoodDonation, DonationRequest, Volunteer, BeneficiaryDemand
from app.tools.geo_tools import calculate_distance_km


class AllocationEngine:
    """Deterministic Multi-Factor Scoring Engine for NGO Food and Ingredient Allocation."""

    @classmethod
    def evaluate_ngo(cls, donation: FoodDonation, ngo: NGO) -> dict:
        """
        Evaluate an NGO for a specific food or ingredient donation.
        Returns a score (0 - 100) and an explainable component breakdown.
        """
        breakdown = {
            "category_score": 0.0,
            "storage_score": 0.0,
            "distance_score": 0.0,
            "capacity_score": 0.0,
            "volunteer_score": 0.0,
            "fairness_score": 0.0,
            "raw_distance_km": 0.0,
            "est_travel_time_mins": 0,
            "reasons": [],
            "disqualified": False,
            "disqualification_reason": None
        }

        don_cat = (donation.donation_category or "prepared_food").lower()
        sub_cat = (donation.category or "").lower()
        food_name = (donation.food_name or "").lower()

        # 1. Category & Active Beneficiary Demand Compatibility (Max: 30 pts)
        # Check NGO accepted categories
        accepted_cats = [c.strip().lower() for c in (ngo.accepted_categories or "prepared_food,fresh_produce,raw_ingredients").split(",") if c.strip()]
        if don_cat not in accepted_cats and "all" not in accepted_cats:
            breakdown["disqualified"] = True
            breakdown["disqualification_reason"] = f"NGO does not accept '{don_cat}' donations."
            breakdown["reasons"].append(f"Category mismatch: NGO only handles {', '.join(accepted_cats)}")
            breakdown["total_score"] = 0.0
            breakdown["summary"] = f"Ineligible: NGO does not accept {don_cat}."
            return breakdown

        # Check Active Beneficiary Demands for this NGO
        active_demands = BeneficiaryDemand.query.filter_by(
            ngo_id=ngo.id, status='active'
        ).all()

        demand_conflict = False
        demand_match = False
        demand_pts = 0.0

        if active_demands:
            # Check if there is an exact or category demand match
            for d in active_demands:
                d_cat = (d.donation_category or "prepared_food").lower()
                d_item = (d.category or "").lower()

                # CRITICAL RULE: If NGO has an active demand for raw ingredients (e.g. rice, pulses),
                # and this donation is prepared food (cooked meals), do NOT match!
                if d_cat == "raw_ingredients" and don_cat == "prepared_food":
                    demand_conflict = True
                    break
                elif d_cat == "prepared_food" and don_cat == "raw_ingredients":
                    # NGO specifically requested immediate cooked meals, not raw grains to cook
                    if not any(k in (ngo.storage_facilities or "") for k in ["community_kitchen", "dining_hall"]):
                        demand_conflict = True
                        break

                if d_cat == don_cat or d_item in sub_cat or d_item in food_name:
                    demand_match = True
                    if d.urgency_level in ['urgent', 'critical']:
                        demand_pts = 30.0
                        breakdown["reasons"].append(f"Critical priority: NGO has active high-urgency demand for '{d.category}'")
                    else:
                        demand_pts = 25.0
                        breakdown["reasons"].append(f"Direct match: NGO has active logged demand for '{d.category}'")
                    break

        if demand_conflict:
            breakdown["disqualified"] = True
            breakdown["disqualification_reason"] = "Active demand conflict: NGO specifically requested different food category."
            breakdown["reasons"].append("Demand mismatch: NGO requested raw staples/rice, not prepared meals.")
            breakdown["category_score"] = 0.0
            breakdown["total_score"] = 0.0
            breakdown["summary"] = "Ineligible: Active NGO demand is for raw ingredients, not prepared meals."
            return breakdown

        if demand_match:
            cat_pts = demand_pts
        else:
            # Baseline compatibility from food_preferences
            ngo_prefs = [p.strip().lower() for p in (ngo.food_preferences or "").split(",") if p.strip()]
            if not ngo_prefs or "all" in ngo_prefs or any(p in sub_cat for p in ngo_prefs) or don_cat in ngo_prefs:
                cat_pts = 20.0
                breakdown["reasons"].append(f"Standard category compatibility for '{don_cat}'")
            else:
                cat_pts = 10.0
                breakdown["reasons"].append(f"Partial category compatibility ('{don_cat}')")

        breakdown["category_score"] = cat_pts

        # 2. Storage Facility Alignment (Max: 15 pts)
        facilities = [f.strip().lower() for f in (ngo.storage_facilities or "dining_hall,dry_pantry,cold_storage").split(",") if f.strip()]
        storage_pts = 10.0  # default baseline

        if don_cat == "raw_ingredients":
            if any(f in facilities for f in ["dry_pantry", "warehouse", "grain_storage"]):
                storage_pts = 15.0
                breakdown["reasons"].append("Optimal storage: NGO has verified dry warehouse/pantry for bulk ingredients.")
            else:
                storage_pts = 5.0
                breakdown["reasons"].append("Limited storage: NGO lacks designated dry warehouse for bulk ingredients.")
        elif don_cat == "fresh_produce":
            if any(f in facilities for f in ["cold_storage", "refrigerator", "aerated_storage", "cool_pantry"]):
                storage_pts = 15.0
                breakdown["reasons"].append("Optimal storage: NGO equipped with cool/aerated storage for produce freshness.")
            else:
                storage_pts = 8.0
                breakdown["reasons"].append("Adequate storage for immediate fresh produce distribution.")
        else:  # prepared_food
            if any(f in facilities for f in ["dining_hall", "community_kitchen", "hot_holding"]):
                storage_pts = 15.0
                breakdown["reasons"].append("Optimal facility: NGO has dining hall/community kitchen for immediate serving.")
            else:
                storage_pts = 10.0
                breakdown["reasons"].append("Standard facility: Suitable for immediate meal packet distribution.")

        breakdown["storage_score"] = storage_pts

        # 3. Distance & Transit Urgency Decay (Max: 20 pts)
        try:
            distance = calculate_distance_km(
                donation.latitude, donation.longitude,
                ngo.latitude, ngo.longitude
            )
        except Exception:
            distance = 25.0

        breakdown["raw_distance_km"] = distance
        est_mins = int(distance * 3 + 8)
        breakdown["est_travel_time_mins"] = est_mins

        # Category-dependent distance tolerances
        if don_cat == "prepared_food":
            # Perishable hot meals require short radius
            if distance <= 2.5:
                dist_pts = 20.0
                breakdown["reasons"].append(f"Hyperlocal transit ({distance:.1f} km, ~{est_mins} mins)")
            elif distance <= 10.0:
                dist_pts = max(0.0, 20.0 * (1.0 - (distance - 2.5) / 7.5))
                breakdown["reasons"].append(f"Manageable transit distance ({distance:.1f} km, ~{est_mins} mins)")
            else:
                dist_pts = 0.0
                breakdown["reasons"].append(f"Transit distance ({distance:.1f} km) exceeds optimal hot meal rescue radius")
        elif don_cat == "fresh_produce":
            # Produce can travel medium distances
            if distance <= 5.0:
                dist_pts = 20.0
                breakdown["reasons"].append(f"Local transit ({distance:.1f} km, ~{est_mins} mins)")
            elif distance <= 20.0:
                dist_pts = max(0.0, 20.0 * (1.0 - (distance - 5.0) / 15.0))
                breakdown["reasons"].append(f"Moderate transit distance ({distance:.1f} km)")
            else:
                dist_pts = 2.0
                breakdown["reasons"].append(f"Extended transit ({distance:.1f} km) for produce batch")
        else:
            # Raw ingredients (shelf stable, grains, flour) can travel wider metropolitan radius
            if distance <= 8.0:
                dist_pts = 20.0
                breakdown["reasons"].append(f"Proximity bonus ({distance:.1f} km)")
            elif distance <= 30.0:
                dist_pts = max(5.0, 20.0 * (1.0 - (distance - 8.0) / 22.0))
                breakdown["reasons"].append(f"Acceptable transit for shelf-stable staples ({distance:.1f} km)")
            else:
                dist_pts = 4.0
                breakdown["reasons"].append(f"Long-distance raw ingredient transit ({distance:.1f} km)")

        breakdown["distance_score"] = round(dist_pts, 1)

        # 4. Capacity Compatibility (Max: 15 pts)
        quantity = donation.quantity or 1
        ngo_cap = ngo.capacity_people or 1

        if don_cat == "raw_ingredients":
            # For raw ingredients, 1 kg provides ~2-3 meals
            equiv_servings = quantity * 2.5
        elif donation.unit == 'kg':
            equiv_servings = quantity * 2.5
        else:
            equiv_servings = quantity

        if ngo_cap < equiv_servings * 0.5:
            cap_pts = 5.0
            breakdown["reasons"].append(f"Batch volume ({int(equiv_servings)} servings) exceeds NGO capacity ({ngo_cap})")
        else:
            ratio = equiv_servings / ngo_cap
            if 0.15 <= ratio <= 1.2:
                cap_pts = 15.0
                breakdown["reasons"].append(f"Optimal capacity utilization ({ngo_cap} beneficiaries)")
            elif ratio > 0.05:
                cap_pts = 12.0
                breakdown["reasons"].append(f"Adequate capacity ({ngo_cap} people)")
            else:
                cap_pts = 8.0
                breakdown["reasons"].append(f"Large capacity NGO for relatively small donation batch")

        breakdown["capacity_score"] = cap_pts

        # 5. Volunteer Availability & Vehicle Readiness (Max: 10 pts)
        nearby_volunteers = Volunteer.query.filter_by(available=True).all()
        has_suitable_vol = False
        for v in nearby_volunteers:
            try:
                v_dist = calculate_distance_km(v.latitude, v.longitude, donation.latitude, donation.longitude)
                # Raw bulk sacks or large produce crates benefit from car/van
                if v_dist <= 10.0:
                    if don_cat in ["raw_ingredients", "fresh_produce"] and donation.quantity > 30:
                        if v.vehicle_type in ['car', 'van', 'bike']:
                            has_suitable_vol = True
                            break
                    else:
                        has_suitable_vol = True
                        break
            except Exception:
                continue

        if has_suitable_vol:
            vol_pts = 10.0
            breakdown["reasons"].append("Couriers with compatible vehicles available in local sector")
        elif nearby_volunteers:
            vol_pts = 5.0
            breakdown["reasons"].append("Volunteers available in wider metropolitan radius")
        else:
            vol_pts = 2.0
            breakdown["reasons"].append("No active courier currently online nearby")

        breakdown["volunteer_score"] = vol_pts

        # 6. Fair Allocation Balance (Max: 10 pts)
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
            breakdown["category_score"] +
            breakdown["storage_score"] +
            breakdown["distance_score"] +
            breakdown["capacity_score"] +
            breakdown["volunteer_score"] +
            breakdown["fairness_score"]
        )
        total_score = round(min(100.0, max(0.0, total_score)), 1)
        breakdown["total_score"] = total_score

        # Structured explainability summary
        summary = (
            f"Overall Match: {total_score}/100. "
            f"Category & Demand: {breakdown['category_score']}/30. "
            f"Storage Fit: {breakdown['storage_score']}/15. "
            f"Transit & Distance: {breakdown['distance_score']}/20 ({distance:.1f} km). "
            f"Capacity Fit: {breakdown['capacity_score']}/15. "
            f"Courier Readiness: {breakdown['volunteer_score']}/10. "
            f"Fairness Balance: {breakdown['fairness_score']}/10."
        )
        breakdown["summary"] = summary
        return breakdown

    @classmethod
    def rank_ngos_for_donation(cls, donation: FoodDonation) -> list:
        """
        Rank all active verified NGOs for a food or ingredient donation using the 100-pt algorithm.
        Returns sorted list of evaluated NGOs with full breakdown.
        """
        ngos = NGO.query.filter_by(is_active=True).all()
        ranked = []
        for ngo in ngos:
            eval_data = cls.evaluate_ngo(donation, ngo)
            is_eligible = (not eval_data["disqualified"]) and eval_data["category_score"] > 0 and eval_data["total_score"] >= 30.0
            ranked.append({
                "ngo": ngo,
                "ngo_id": ngo.id,
                "name": ngo.organization_name,
                "score": eval_data["total_score"],
                "breakdown": eval_data,
                "distance_km": eval_data["raw_distance_km"],
                "est_travel_time_mins": eval_data["est_travel_time_mins"],
                "eligible": is_eligible
            })

        ranked.sort(key=lambda x: x["score"], reverse=True)
        return ranked
