"""
Annadata Intelligence - Role-Based AI Assistant Service
Executes safe, role-scoped database tools with validated parameters.
Synthesizes answers via OpenRouter LLM when available, and provides deterministic local responses when offline or without an API key.
"""
from datetime import datetime
from app.extensions import db
from app.models import (
    User, Restaurant, NGO, Volunteer, FoodDonation,
    DonationRequest, RescueMission, AgentExecutionLog, ImpactRecord
)
from app.services.llm_service import LLMService
from app.services.emergency_service import EmergencyRescueService
from app.services.impact_service import ImpactAnalyticsService
from app.services.forecast_service import SurplusForecastingService


class AssistantService:
    """Safe, Role-Scoped AI Assistant Controller."""

    # ------------------ SAFE ROLE TOOLS ------------------

    @classmethod
    def tool_restaurant_stats(cls, user: User) -> dict:
        rest = Restaurant.query.filter_by(user_id=user.id).first()
        if not rest:
            return {"error": "Restaurant profile not linked"}
        donations = FoodDonation.query.filter_by(restaurant_id=rest.id).all()
        total = len(donations)
        delivered = [d for d in donations if d.status in ['delivered', 'completed']]
        active = [d for d in donations if d.status not in ['delivered', 'completed', 'unsuitable', 'cancelled']]
        return {
            "business_name": rest.business_name,
            "total_donations": total,
            "completed_rescues": len(delivered),
            "active_in_pipeline": len(active),
            "recent_donations": [
                {"food": d.food_name, "quantity": f"{d.quantity} {d.unit}", "status": d.status}
                for d in donations[-3:]
            ]
        }

    @classmethod
    def tool_ngo_requests(cls, user: User) -> dict:
        ngo = NGO.query.filter_by(user_id=user.id).first()
        if not ngo:
            return {"error": "NGO profile not linked"}
        requests = DonationRequest.query.filter_by(ngo_id=ngo.id, status='pending').all()
        active_missions = RescueMission.query.filter(
            RescueMission.ngo_id == ngo.id,
            RescueMission.status.in_(['ngo_accepted', 'volunteer_assigned', 'pickup_initiated', 'food_collected', 'delivery_initiated'])
        ).all()
        return {
            "ngo_name": ngo.organization_name,
            "capacity": ngo.capacity_people,
            "pending_requests_count": len(requests),
            "pending_requests": [
                {
                    "id": r.id,
                    "food": r.donation.food_name if r.donation else "Food Item",
                    "quantity": f"{r.donation.quantity} {r.donation.unit}" if r.donation else "N/A",
                    "distance_km": r.distance_km,
                    "score": r.match_score
                }
                for r in requests[:4]
            ],
            "active_missions_count": len(active_missions)
        }

    @classmethod
    def tool_volunteer_missions(cls, user: User) -> dict:
        vol = Volunteer.query.filter_by(user_id=user.id).first()
        if not vol:
            return {"error": "Volunteer profile not linked"}
        missions = RescueMission.query.filter(
            RescueMission.volunteer_id == vol.id,
            RescueMission.status.in_(['volunteer_assigned', 'pickup_initiated', 'food_collected', 'delivery_initiated', 'delayed'])
        ).all()
        return {
            "volunteer_name": user.full_name,
            "available": vol.available,
            "active_missions_count": len(missions),
            "active_missions": [
                {
                    "code": m.mission_code,
                    "status": m.status,
                    "food": m.donation.food_name if m.donation else "N/A",
                    "pickup_at": m.donation.location_address if m.donation else "N/A",
                    "deliver_to": m.destination_ngo.organization_name if m.destination_ngo else "N/A",
                    "deadline": m.pickup_deadline.strftime("%H:%M") if m.pickup_deadline else "ASAP"
                }
                for m in missions[:3]
            ]
        }

    @classmethod
    def tool_admin_overview(cls, user: User) -> dict:
        if user.role != 'admin':
            return {"error": "Unauthorized access"}
        return {
            "total_users": User.query.count(),
            "total_restaurants": Restaurant.query.count(),
            "total_ngos": NGO.query.count(),
            "total_volunteers": Volunteer.query.count(),
            "total_donations": FoodDonation.query.count(),
            "active_missions": RescueMission.query.filter(
                RescueMission.status.notin_(['completed', 'cancelled'])
            ).count(),
            "agent_failures": AgentExecutionLog.query.filter_by(status='failed').count()
        }

    # ------------------ QUERY RESOLUTION ------------------

    @classmethod
    def chat(cls, user: User, message: str) -> dict:
        """
        Process a user question with role-aware safety, executing authorized tools
        and returning an explainable, data-backed answer.
        """
        msg_lower = message.lower()
        role = user.role if user.is_authenticated else 'public'

        # Gather authorized data context based on role
        context_data = {}
        if role == 'restaurant':
            context_data = cls.tool_restaurant_stats(user)
        elif role == 'ngo':
            context_data = cls.tool_ngo_requests(user)
        elif role == 'volunteer':
            context_data = cls.tool_volunteer_missions(user)
        elif role == 'admin':
            context_data = cls.tool_admin_overview(user)

        # Emergency check
        emergencies = EmergencyRescueService.scan_and_escalate(threshold_hours=2.0)
        emergency_count = len(emergencies)

        # Check if LLM is available
        llm = LLMService()
        if llm.available:
            prompt = (
                f"You are 'Annadata Intelligence', an AI assistant for the ANNADATA AI food rescue network. "
                f"The user has role: '{role}' and name: '{user.full_name}'.\n"
                f"Current Database Context for this user: {context_data}\n"
                f"Current Platform Emergency Alerts count: {emergency_count}\n"
                f"User Question: '{message}'\n"
                f"Instructions: Provide a concise, highly helpful, professional response based STRICTLY on the provided data. "
                f"Do not invent facts. If suggesting actions, tailor them specifically to their '{role}' role. "
                f"Format key details with bullet points."
            )
            response_text = llm.generate(prompt, max_tokens=300)
            if response_text:
                return {
                    "answer": response_text.strip(),
                    "source": "AI Model (OpenRouter)",
                    "role": role,
                    "context_summary": context_data
                }

        # Deterministic Rule-Based Fallback when LLM is unavailable or offline
        fallback_answer = cls._generate_deterministic_response(role, user, msg_lower, context_data, emergency_count)
        return {
            "answer": fallback_answer,
            "source": "Annadata Deterministic Engine (Offline / Local Mode)",
            "role": role,
            "context_summary": context_data
        }

    @classmethod
    def _generate_deterministic_response(cls, role: str, user: User, msg: str, data: dict, emergency_count: int) -> str:
        """High-quality deterministic fallback responses with real database values."""

        if role == 'restaurant':
            if any(k in msg for k in ['when', 'time', 'predict', 'schedule', 'surplus']):
                return (
                    "**Optimal Surplus Donation Guidance:**\n\n"
                    "• **Peak Timing:** Based on metropolitan hospitality data, optimal donation windows are **15:30 - 17:00** (post-lunch) and **21:30 - 23:00** (post-dinner).\n"
                    "• **Advance Notice:** Posting 60–90 minutes before kitchen close allows the matching engine to coordinate volunteer pickup before collection deadlines.\n"
                    "• **Safety Window:** Cooked hot meals should have a collection deadline set within 3–4 hours of preparation."
                )
            elif any(k in msg for k in ['category', 'accept', 'food', 'guideline']):
                return (
                    "**Accepted Food Categories:**\n\n"
                    "• Cooked Meals (Curries, Rice dishes, Rotis/Bread)\n"
                    "• Baked Goods (Bread, Pastries, Buns)\n"
                    "• Fresh Fruits & Raw Produce\n"
                    "• Packaged Vegetarian & Vegan provisions\n"
                    "• Dairy products with verified cold storage.\n\n"
                    "*(Note: Expired items or foods kept at room temperature for over 4 hours cannot pass safety screening.)*"
                )
            else:
                total = data.get('total_donations', 0)
                completed = data.get('completed_rescues', 0)
                active = data.get('active_in_pipeline', 0)
                return (
                    f"**Donation Status for {data.get('business_name', 'your restaurant')}:**\n\n"
                    f"• **Total Donations Created:** {total}\n"
                    f"• **Successfully Delivered Rescues:** {completed}\n"
                    f"• **Active in Pipeline:** {active}\n"
                    f"• **Emergency Network Alerts:** {emergency_count} urgent rescues active in the network.\n\n"
                    f"Use the **'New Donation'** wizard on your dashboard to post a surplus batch."
                )

        elif role == 'ngo':
            if any(k in msg for k in ['urgent', 'emergency', 'alert', 'deadline']):
                if emergency_count > 0:
                    return f"**Emergency Alert:** There are currently **{emergency_count} urgent food rescue donations** within the network approaching their collection deadline. Check your dashboard requests immediately to accept!"
                return "There are currently no urgent emergency food rescue alerts requiring immediate action in your sector."
            elif any(k in msg for k in ['capacity', 'demand', 'people', 'limit']):
                cap = data.get('capacity', 0)
                return (
                    f"**Capacity Overview:**\n\n"
                    f"• Your registered beneficiary capacity is **{cap} people**.\n"
                    f"• The Smart Allocation Engine uses this capacity to ensure you are matched with donations you can safely store and distribute without wastage.\n"
                    f"• You can update your capacity or log specific community meal demands on your NGO dashboard."
                )
            else:
                pending = data.get('pending_requests_count', 0)
                active = data.get('active_missions_count', 0)
                return (
                    f"**NGO Status for {data.get('ngo_name', 'your organization')}:**\n\n"
                    f"• **Pending Donation Requests:** {pending} awaiting your review.\n"
                    f"• **Active Rescue Missions:** {active} currently in transit.\n"
                    f"• **Emergency Alerts:** {emergency_count} network alerts.\n\n"
                    f"Visit your dashboard to review match scores and accept incoming donations."
                )

        elif role == 'volunteer':
            if any(k in msg for k in ['next', 'mission', 'assigned', 'pickup']):
                active_count = data.get('active_missions_count', 0)
                missions = data.get('active_missions', [])
                if missions:
                    top = missions[0]
                    return (
                        f"**Your Next Assigned Mission: {top['code']}**\n\n"
                        f"• **Food Item:** {top['food']}\n"
                        f"• **Pickup Location:** {top['pickup_at']}\n"
                        f"• **Delivery Destination:** {top['deliver_to']}\n"
                        f"• **Collection Deadline:** {top['deadline']}\n"
                        f"• **Current Status:** `{top['status']}`\n\n"
                        f"Please navigate to your Volunteer Dashboard to update status when you depart for pickup."
                    )
                return f"You currently have no active assigned rescue missions. You have {active_count} assignments. Toggle your availability on the dashboard to receive new pickups."
            elif any(k in msg for k in ['instruction', 'protocol', 'step', 'how']):
                return (
                    "**Volunteer Rescue Protocol:**\n\n"
                    "1. **Accept Assignment:** Acknowledge mission on your dashboard.\n"
                    "2. **Pickup Food:** Inspect packaging integrity and verify Food Rescue Passport QR code.\n"
                    "3. **Mark 'Food Rescued':** Click the collected button in your dashboard.\n"
                    "4. **Transport:** Keep food level and protected during transit.\n"
                    "5. **Handover & Verification:** Deliver to NGO contact and enter delivery verification PIN."
                )
            else:
                return (
                    f"**Volunteer Dispatch Summary:**\n\n"
                    f"• Availability: **{'Online & Ready' if data.get('available') else 'Offline / On Break'}**\n"
                    f"• Active Missions: **{data.get('active_missions_count', 0)}**\n"
                    f"• Urgent Network Rescues: **{emergency_count}**\n\n"
                    f"Thank you for powering the Annadata community rescue network!"
                )

        elif role == 'admin':
            return (
                f"**ANNADATA AI Platform Operations Summary:**\n\n"
                f"• **Total Registered Users:** {data.get('total_users', 0)}\n"
                f"• **Verified Food Donors:** {data.get('total_restaurants', 0)}\n"
                f"• **Partner NGOs:** {data.get('total_ngos', 0)}\n"
                f"• **Active Volunteers:** {data.get('total_volunteers', 0)}\n"
                f"• **Total Rescues Recorded:** {data.get('total_donations', 0)}\n"
                f"• **Active Missions in Flight:** {data.get('active_missions', 0)}\n"
                f"• **Agent Failures Logged:** {data.get('agent_failures', 0)}\n"
                f"• **Active Emergency Flags:** {emergency_count}"
            )

        # Public guest fallback
        return (
            "Welcome to **ANNADATA AI — Intelligent Food Rescue & Community Impact Network**.\n\n"
            "We connect food businesses, non-profits, and volunteers to eradicate food waste and hunger using predictive AI and transparent tracking.\n\n"
            "Please **Sign In** or **Register** to access role-specific dashboards and personalized intelligence."
        )
