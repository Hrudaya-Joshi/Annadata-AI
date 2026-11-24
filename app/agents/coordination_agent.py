import json
from app.agents.base_agent import BaseAgent
from app.models import FoodDonation, DonationRequest, Volunteer, NGO, PickupAssignment, RescueMission
from app.tools.geo_tools import calculate_distance_km
from app.services.llm_service import LLMService
from app.services.mission_service import MissionService
from app.extensions import db


class CoordinationAgent(BaseAgent):
    name = "CoordinationAgent"

    def __init__(self):
        self.llm = LLMService()

    def run(self, donation_id, ngo_id=None, volunteer_id=None):
        donation = FoodDonation.query.get(donation_id)
        if not donation:
            return {"error": "Donation not found"}

        input_data = {"donation_id": donation_id, "ngo_id": ngo_id, "volunteer_id": volunteer_id}

        try:
            if ngo_id is None:
                ngo = NGO.query.filter_by(is_active=True).first()
            else:
                ngo = NGO.query.get(ngo_id)

            if not ngo:
                return {"error": "NGO not found"}

            distance = calculate_distance_km(
                donation.latitude, donation.longitude,
                ngo.latitude, ngo.longitude
            )

            # Check or create DonationRequest
            request = DonationRequest.query.filter_by(
                donation_id=donation_id,
                ngo_id=ngo.id
            ).first()

            if not request:
                request = DonationRequest(
                    donation_id=donation_id,
                    ngo_id=ngo.id,
                    distance_km=distance,
                    status="accepted" if volunteer_id else "pending"
                )
                db.session.add(request)
                db.session.flush()

            # Find volunteer
            if volunteer_id is None:
                volunteer = Volunteer.query.filter_by(available=True).first()
            else:
                volunteer = Volunteer.query.get(volunteer_id)

            assignment = None
            if volunteer:
                assignment = PickupAssignment.query.filter_by(request_id=request.id).first()
                if not assignment:
                    assignment = PickupAssignment(
                        request_id=request.id,
                        volunteer_id=volunteer.id,
                        status="assigned"
                    )
                    db.session.add(assignment)
                volunteer.available = False
                request.status = "accepted"

            # Create or update tracked RescueMission
            mission = RescueMission.query.filter_by(donation_id=donation.id).first()
            if not mission:
                mission = MissionService.create_mission_for_request(donation, ngo, volunteer)

            prompt = (
                f"Suggest pickup arrangements for {donation.quantity} {donation.unit} of "
                f"{donation.food_name} from {donation.location_address} to {ngo.organization_name}. "
                f"Distance: {distance} km."
            )
            suggestion = self.llm.generate(prompt, max_tokens=150)
            if not suggestion:
                suggestion = (
                    f"Optimal route: Transit ~{int(distance * 3 + 8)} mins. "
                    f"Inspect food packaging on arrival and confirm pickup via Food Rescue Passport."
                )

            donation.status = "matched"
            db.session.commit()

            output = {
                "request_id": request.id,
                "ngo_id": ngo.id,
                "distance_km": distance,
                "volunteer_id": volunteer.id if volunteer else None,
                "assignment_id": assignment.id if assignment else None,
                "mission_id": mission.id if mission else None,
                "mission_code": mission.mission_code if mission else None,
                "suggestion": suggestion,
            }

            self.log(donation_id, "coordinate", input_data, output, "success")
            return output

        except Exception as e:
            db.session.rollback()
            self.log(donation_id, "coordinate", input_data, None, "failed", str(e))
            return {"error": str(e)}
