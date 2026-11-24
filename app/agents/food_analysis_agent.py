import json
from datetime import datetime
import random
from app.agents.base_agent import BaseAgent
from app.tools.safety_rules import evaluate
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
            f"suggest one category from: vegetarian, non-vegetarian, vegan, beverages, snacks, "
            f"dairy, baked goods, fruits, cooked meals, other. Return only the single category name in lowercase."
        )
        result = self.llm.generate(prompt, max_tokens=30)
        if result:
            cleaned = result.strip().lower().replace(".", "").replace('"', '').replace("'", "")
            return cleaned
        return "cooked meals"

    def run(self, donation_id, safety_checklist: dict = None):
        donation = FoodDonation.query.get(donation_id)
        if not donation:
            return {"error": "Donation not found"}

        input_data = {
            "donation_id": donation_id,
            "food_name": donation.food_name,
            "quantity": donation.quantity
        }

        try:
            # 1. Category inference if missing
            if not donation.category or donation.category == "other":
                donation.category = self.categorize_with_llm(donation.food_name, donation.description or "")

            # 2. Unique Rescue Passport code generation if missing
            if not donation.rescue_code:
                date_part = datetime.utcnow().strftime("%Y%m%d")
                rand_part = random.randint(1000, 9999)
                donation.rescue_code = f"ANN-RESCUE-{date_part}-{rand_part}"

            # 3. Deterministic Safety Evaluation (safety_rules.py)
            suitable, issues = evaluate(donation)

            # 4. Integrate FoodSafetyAssessment
            assessment = FoodSafetyAssessment.query.filter_by(donation_id=donation.id).first()
            if not assessment:
                checklist = safety_checklist or {}
                assessment = FoodSafetyAssessment(
                    donation_id=donation.id,
                    visual_inspection_passed=checklist.get('visual_inspection_passed', True),
                    packaging_intact=checklist.get('packaging_intact', True),
                    temperature_controlled=checklist.get('temperature_controlled', True),
                    allergens_declared=checklist.get('allergens_declared', True),
                    hygiene_verified=checklist.get('hygiene_verified', True),
                    temperature_celsius=float(checklist.get('temperature_celsius', 4.0 if donation.category == 'dairy' else 65.0)),
                    risk_level='low' if suitable else 'high',
                    ai_risk_observations="Standard compliance verified." if suitable else "; ".join(issues)
                )
                db.session.add(assessment)
            else:
                if not suitable:
                    assessment.risk_level = 'high'
                    assessment.ai_risk_observations = "; ".join(issues)

            # 5. Suitability score calculation
            suitability_score = 100.0 if suitable else 0.0
            if suitable and assessment.temperature_celsius and assessment.temperature_celsius > 60.0:
                suitability_score = 98.0  # optimal hot holding

            report = {
                "suitable": suitable,
                "issues": issues,
                "category": donation.category,
                "quantity": donation.quantity,
                "rescue_code": donation.rescue_code,
                "risk_level": assessment.risk_level,
                "suitability_score": suitability_score,
                "expiry_time": donation.expiry_time.isoformat(),
                "collection_deadline": donation.collection_deadline.isoformat(),
            }

            donation.analysis_report = json.dumps(report)
            donation.suitability_score = suitability_score
            donation.status = "suitable" if suitable else "unsuitable"

            db.session.commit()
            self.log(donation_id, "analyze", input_data, report, "success")
            return report

        except Exception as e:
            db.session.rollback()
            self.log(donation_id, "analyze", input_data, None, "failed", str(e))
            return {"error": str(e)}
