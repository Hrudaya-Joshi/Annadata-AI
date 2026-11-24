import json
from datetime import datetime
import random
from app.agents.base_agent import BaseAgent
from app.tools.safety_rules import (
    evaluate,
    evaluate_prepared_food,
    evaluate_fresh_produce,
    evaluate_raw_ingredients
)
from app.services.llm_service import LLMService
from app.extensions import db
from app.models import FoodDonation, FoodSafetyAssessment


class FoodAnalysisAgent(BaseAgent):
    name = "FoodAnalysisAgent"

    def __init__(self):
        self.llm = LLMService()

    def categorize_with_llm(self, food_name, description):
        prompt = (
            f"Given food name '{food_name}' and description '{description}', "
            f"suggest the primary donation category and food type. "
            f"Return JSON with 'donation_category' (one of: prepared_food, fresh_produce, raw_ingredients) "
            f"and 'category' (sub-category name). Example: {{\"donation_category\": \"prepared_food\", \"category\": \"cooked meals\"}}"
        )
        result = self.llm.generate(prompt, max_tokens=60)
        if result:
            try:
                data = json.loads(result.strip())
                return data.get("donation_category", "prepared_food"), data.get("category", "cooked meals")
            except Exception:
                pass
        return "prepared_food", "cooked meals"

    def run(self, donation_id, safety_checklist: dict = None):
        donation = FoodDonation.query.get(donation_id)
        if not donation:
            return {"error": "Donation not found"}

        input_data = {
            "donation_id": donation_id,
            "donation_category": donation.donation_category,
            "food_name": donation.food_name,
            "quantity": donation.quantity
        }

        try:
            # 1. Ensure donation_category is set
            if not donation.donation_category:
                cat_lower = (donation.category or "").lower()
                if any(k in cat_lower for k in ["fruit", "vegetable", "produce", "greens"]):
                    donation.donation_category = "fresh_produce"
                elif any(k in cat_lower for k in ["grain", "rice", "wheat", "flour", "pulse", "lentil", "staple", "oil"]):
                    donation.donation_category = "raw_ingredients"
                else:
                    donation.donation_category = "prepared_food"

            # 2. Subcategory inference if missing
            if not donation.category or donation.category == "other":
                d_cat, sub_cat = self.categorize_with_llm(donation.food_name, donation.description or "")
                donation.donation_category = d_cat
                donation.category = sub_cat

            # 3. Unique Rescue Passport code generation if missing
            if not donation.rescue_code:
                date_part = datetime.utcnow().strftime("%Y%m%d")
                rand_part = random.randint(1000, 9999)
                donation.rescue_code = f"ANN-RESCUE-{date_part}-{rand_part}"

            # 4. Category-Specific Safety Evaluation
            checklist = safety_checklist or {}
            d_cat = donation.donation_category.lower()

            if d_cat == "fresh_produce":
                eval_res = evaluate_fresh_produce(donation)
            elif d_cat == "raw_ingredients":
                eval_res = evaluate_raw_ingredients(donation)
            else:
                eval_res = evaluate_prepared_food(donation)

            suitable = eval_res["suitable"]
            issues = eval_res["issues"]
            checks = eval_res["checks"]
            recommendations = eval_res["recommendations"]
            req_human = eval_res["requires_human_verification"]
            risk_lvl = eval_res["risk_level"]

            # Merge manual checklist flags
            if not checklist.get("visual_inspection_passed", True):
                suitable = False
                issues.append("Visual or olfactory inspection check failed.")
                risk_lvl = "high"
                req_human = True

            if not checklist.get("packaging_intact", True):
                issues.append("Packaging reported not intact or unsealed.")
                req_human = True
                if risk_lvl == "low":
                    risk_lvl = "medium"

            # 5. Integrate FoodSafetyAssessment
            assessment = FoodSafetyAssessment.query.filter_by(donation_id=donation.id).first()
            if not assessment:
                assessment = FoodSafetyAssessment(
                    donation_id=donation.id,
                    visual_inspection_passed=checklist.get('visual_inspection_passed', True),
                    packaging_intact=checklist.get('packaging_intact', True),
                    temperature_controlled=checklist.get('temperature_controlled', True),
                    allergens_declared=checklist.get('allergens_declared', True),
                    hygiene_verified=checklist.get('hygiene_verified', True),
                    temperature_celsius=float(checklist.get('temperature_celsius', 65.0 if d_cat == 'prepared_food' else 22.0)),
                    risk_level=risk_lvl,
                    requires_human_verification=req_human,
                    category_checks=json.dumps(checks),
                    safety_recommendations="; ".join(recommendations),
                    ai_risk_observations="Verified against safety standards." if suitable else "; ".join(issues)
                )
                db.session.add(assessment)
            else:
                assessment.risk_level = risk_lvl
                assessment.requires_human_verification = req_human
                assessment.category_checks = json.dumps(checks)
                assessment.safety_recommendations = "; ".join(recommendations)
                assessment.ai_risk_observations = "; ".join(issues) if issues else "Verified against safety standards."

            # 6. Suitability score calculation
            suitability_score = 100.0 if suitable else 0.0
            if suitable:
                if d_cat == "prepared_food":
                    temp_c = assessment.temperature_celsius or 0.0
                    if temp_c >= 60.0 or (temp_c <= 5.0 and temp_c > -2.0):
                        suitability_score = 98.0  # Optimal active temperature
                    elif req_human:
                        suitability_score = 82.0
                elif d_cat == "fresh_produce":
                    if "fresh" in (donation.freshness_condition or "").lower():
                        suitability_score = 95.0
                    elif req_human:
                        suitability_score = 80.0
                elif d_cat == "raw_ingredients":
                    if "seal" in (donation.packaging_condition or "").lower():
                        suitability_score = 98.0
                    elif req_human:
                        suitability_score = 85.0

            donation.requires_human_verification = req_human
            donation.suitability_score = suitability_score
            donation.status = "suitable" if suitable else "unsuitable"

            report = {
                "suitable": suitable,
                "issues": issues,
                "donation_category": donation.donation_category,
                "category": donation.category,
                "quantity": donation.quantity,
                "unit": donation.unit,
                "rescue_code": donation.rescue_code,
                "risk_level": assessment.risk_level,
                "requires_human_verification": req_human,
                "suitability_score": suitability_score,
                "checks": checks,
                "recommendations": recommendations,
                "collection_deadline": donation.collection_deadline.isoformat(),
            }

            donation.analysis_report = json.dumps(report)
            db.session.commit()
            self.log(donation_id, "analyze", input_data, report, "success")
            return report

        except Exception as e:
            db.session.rollback()
            err_msg = str(e)
            self.log(donation_id, "analyze", input_data, {"error": err_msg}, "error", err_msg)
            return {"error": err_msg}
