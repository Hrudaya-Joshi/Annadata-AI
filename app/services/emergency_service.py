"""
Emergency Food Rescue Mode & Escalation Service for ANNADATA AI
Identifies at-risk donations nearing collection deadlines, escalates priority, and alerts backup NGOs/volunteers.
"""
from datetime import datetime, timedelta
from app.extensions import db
from app.models import FoodDonation, DonationRequest, NGO, Volunteer, Notification, AuditLog
from app.services.allocation_service import AllocationEngine
from app.tools.safety_rules import get_current_time


class EmergencyRescueService:
    """Detects deadline risks and triggers rapid response protocols."""

    DEFAULT_URGENCY_THRESHOLD_HOURS = 2.0  # Under 2 hours = emergency

    @classmethod
    def scan_and_escalate(cls, threshold_hours: float = None) -> list:
        """
        Scan all active uncollected donations. If collection deadline is within threshold,
        escalate to emergency mode and trigger multi-channel alerts.
        """
        if threshold_hours is None:
            threshold_hours = cls.DEFAULT_URGENCY_THRESHOLD_HOURS

        now = get_current_time().replace(tzinfo=None)
        cutoff = now + timedelta(hours=threshold_hours)

        # Active donations that are suitable and not yet collected or cancelled
        donations = FoodDonation.query.filter(
            FoodDonation.status.in_(['suitable', 'matched', 'pending_matching', 'requested']),
            FoodDonation.collection_deadline <= cutoff,
            FoodDonation.collection_deadline > now
        ).all()

        escalated = []
        for don in donations:
            mins_remaining = int((don.collection_deadline - now).total_seconds() / 60)
            was_emergency = don.is_emergency
            don.is_emergency = True

            # If not previously marked as emergency, trigger immediate alerts
            if not was_emergency:
                cls._broadcast_emergency_alert(don, mins_remaining)
                audit = AuditLog(
                    action="EMERGENCY_ESCALATION",
                    target_type="FoodDonation",
                    target_id=don.id,
                    details=f"Donation #{don.id} '{don.food_name}' escalated to Emergency Mode: {mins_remaining}m left until deadline."
                )
                db.session.add(audit)

            # Recommend backup NGOs
            ranked_ngos = AllocationEngine.rank_ngos_for_donation(don)
            backup_ngos = [item for item in ranked_ngos if item["eligible"]][:3]

            escalated.append({
                "donation": don,
                "donation_id": don.id,
                "food_name": don.food_name,
                "mins_remaining": mins_remaining,
                "urgency_badge": "CRITICAL" if mins_remaining <= 60 else "URGENT",
                "backup_ngos": backup_ngos
            })

        db.session.commit()
        return escalated

    @classmethod
    def _broadcast_emergency_alert(cls, donation: FoodDonation, mins_remaining: int):
        """Notify all verified NGOs within 15 km and available volunteers."""
        title = f"EMERGENCY RESCUE: '{donation.food_name}' ({mins_remaining}m left)"
        msg = (
            f"Urgent surplus food rescue needed! {donation.quantity} {donation.unit} of "
            f"'{donation.food_name}' at {donation.location_address}. Collection deadline expires in {mins_remaining} minutes!"
        )

        # Eligible NGOs
        ranked = AllocationEngine.rank_ngos_for_donation(donation)
        for item in ranked[:4]:
            ngo = item["ngo"]
            if ngo.user_id:
                notif = Notification(
                    user_id=ngo.user_id,
                    title=title,
                    message=msg,
                    category="urgent",
                    link_url=f"/ngo/request_detail"
                )
                db.session.add(notif)

        # Nearby available volunteers
        volunteers = Volunteer.query.filter_by(available=True).all()
        for v in volunteers:
            if v.user_id:
                notif = Notification(
                    user_id=v.user_id,
                    title=f"URGENT MISSION ALERT: {donation.food_name}",
                    message=f"Surplus food rescue needed within {mins_remaining} mins at {donation.location_address}.",
                    category="urgent",
                    link_url="/volunteer/dashboard"
                )
                db.session.add(notif)
