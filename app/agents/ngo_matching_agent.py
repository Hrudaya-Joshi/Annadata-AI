import json
from app.agents.base_agent import BaseAgent
from app.models import NGO, FoodDonation, DonationRequest
from app.extensions import db
from app.services.allocation_service import AllocationEngine
from app.services.llm_service import LLMService


class NGOMatchingAgent(BaseAgent):
    name = "NGOMatchingAgent"

    def __init__(self):
        self.llm = LLMService()

    def run(self, donation_id):
        donation = FoodDonation.query.get(donation_id)
        if not donation:
            return {"error": "Donation not found"}

        input_data = {"donation_id": donation_id}

        try:
            # Deterministic, multi-factor ranking
            ranked_evals = AllocationEngine.rank_ngos_for_donation(donation)

            results = []
            eligible = []
            created_requests = []

            for item in ranked_evals:
                ngo_dict = {
                    "ngo_id": item["ngo_id"],
                    "name": item["name"],
                    "distance_km": item["distance_km"],
                    "est_travel_time_mins": item["est_travel_time_mins"],
                    "score": round(item["score"], 2),
                    "breakdown": item["breakdown"],
                    "category_match": item["breakdown"]["category_score"] > 0,
                    "capacity_match": item["breakdown"]["capacity_score"] >= 10.0
                }
                results.append(ngo_dict)
                if item["eligible"]:
                    eligible.append(ngo_dict)

            # Prevent duplicate requests and persist matched requests
            for match in eligible:
                existing = DonationRequest.query.filter_by(
                    ngo_id=match["ngo_id"],
                    donation_id=donation.id
                ).first()

                if existing:
                    # Update score if missing
                    if existing.match_score is None:
                        existing.match_score = match["score"]
                        existing.score_breakdown = json.dumps(match["breakdown"])
                    continue

                new_request = DonationRequest(
                    ngo_id=match["ngo_id"],
                    donation_id=donation.id,
                    status="pending",
                    distance_km=match["distance_km"],
                    match_score=match["score"],
                    score_breakdown=json.dumps(match["breakdown"])
                )
                db.session.add(new_request)
                created_requests.append(match["ngo_id"])

            db.session.commit()

            # Generate natural language explanation (LLM or deterministic fallback)
            explanation = ""
            if eligible:
                top = eligible[0]
                if self.llm.available:
                    prompt = (
                        f"Explain concisely in 2 sentences why NGO '{top['name']}' is recommended "
                        f"for donation '{donation.food_name}' ({donation.quantity} {donation.unit}), "
                        f"based on distance {top['distance_km']} km, suitability score {top['score']}/100, "
                        f"and fairness allocation balancing."
                    )
                    explanation = self.llm.generate(prompt, max_tokens=120) or ""

                if not explanation:
                    explanation = top["breakdown"].get("summary", f"Recommended: {top['name']} ({top['score']}/100 match).")

            output = {
                "ranked": results,
                "eligible": eligible,
                "created_requests": created_requests,
                "total_requests": len(created_requests),
                "explanation": explanation
            }

            self.log(donation_id, "match", input_data, output, "success")
            return output

        except Exception as e:
            db.session.rollback()
            self.log(donation_id, "match", input_data, None, "failed", str(e))
            return {"error": str(e)}
