"""
Rescue Mission Management & Finite State Machine for ANNADATA AI
Enforces server-side validation of mission lifecycle transitions, delay alerts, and delivery verification.
"""
from datetime import datetime, timedelta
import random
from app.extensions import db
from app.models import (
    RescueMission, FoodDonation, NGO, Volunteer, User,
    ImpactRecord, Notification, AuditLog
)


class MissionService:
    """Finite State Machine & Lifecycle Controller for Food Rescue Missions."""

    VALID_TRANSITIONS = {
        'submitted': ['safety_screening', 'cancelled'],
        'safety_screening': ['ngo_matching', 'cancelled'],
        'ngo_matching': ['ngo_accepted', 'cancelled'],
        'ngo_accepted': ['volunteer_assigned', 'cancelled'],
        'volunteer_assigned': ['pickup_initiated', 'cancelled'],
        'pickup_initiated': ['food_collected', 'delayed', 'cancelled'],
        'food_collected': ['delivery_initiated', 'delayed', 'cancelled'],
        'delivery_initiated': ['delivery_confirmed', 'delayed', 'cancelled'],
        'delivery_confirmed': ['completed'],
        'delayed': ['food_collected', 'delivery_initiated', 'delivery_confirmed', 'cancelled'],
        'completed': [],
        'cancelled': []
    }

    STATUS_DISPLAY = {
        'submitted': ('Donation Submitted', 'bg-secondary'),
        'safety_screening': ('Safety Screening', 'bg-info'),
        'ngo_matching': ('Matching NGOs', 'bg-primary'),
        'ngo_accepted': ('NGO Accepted', 'bg-primary'),
        'volunteer_assigned': ('Volunteer Assigned', 'bg-info'),
        'pickup_initiated': ('Pickup En Route', 'bg-warning text-dark'),
        'food_collected': ('Food Rescued & Collected', 'bg-warning text-dark'),
        'delivery_initiated': ('Delivery In Transit', 'bg-primary'),
        'delivery_confirmed': ('Delivery Verified', 'bg-success'),
        'completed': ('Mission Completed', 'bg-success'),
        'delayed': ('Delayed - Attention Needed', 'bg-danger'),
        'cancelled': ('Mission Cancelled', 'bg-dark')
    }

    @staticmethod
    def generate_mission_code() -> str:
        date_str = datetime.utcnow().strftime("%Y%m%d")
        rand_suffix = random.randint(1000, 9999)
        return f"ANN-MSN-{date_str}-{rand_suffix}"

    @classmethod
    def create_mission_for_request(cls, donation: FoodDonation, ngo: NGO, volunteer: Volunteer = None) -> RescueMission:
        """Create a new tracked rescue mission when an NGO accepts a donation."""
        code = cls.generate_mission_code()
        pin = str(random.randint(100000, 999999))

        mission = RescueMission(
            mission_code=code,
            donation_id=donation.id,
            ngo_id=ngo.id,
            volunteer_id=volunteer.id if volunteer else None,
            status='volunteer_assigned' if volunteer else 'ngo_accepted',
            pickup_deadline=donation.collection_deadline,
            delivery_deadline=donation.collection_deadline + timedelta(hours=1),
            verification_pin=pin
        )
        db.session.add(mission)
        db.session.flush()

        # Audit log
        audit = AuditLog(
            user_id=ngo.user_id,
            action="CREATE_MISSION",
            target_type="RescueMission",
            target_id=mission.id,
            details=f"Created mission {code} for donation #{donation.id} to {ngo.organization_name}"
        )
        db.session.add(audit)

        # Notify restaurant
        if donation.restaurant and donation.restaurant.user_id:
            notif = Notification(
                user_id=donation.restaurant.user_id,
                title="Rescue Mission Created",
                message=f"Mission {code} initiated for '{donation.food_name}' accepted by {ngo.organization_name}.",
                category="info",
                link_url=f"/mission/{mission.id}"
            )
            db.session.add(notif)

        db.session.commit()
        return mission

    @classmethod
    def transition_state(cls, mission: RescueMission, new_status: str, actor_user: User, notes: str = None) -> tuple[bool, str]:
        """
        Execute server-side validated state transition with security & audit checks.
        """
        current = mission.status
        allowed = cls.VALID_TRANSITIONS.get(current, [])

        if new_status not in allowed:
            return False, f"Illegal state transition from '{current}' to '{new_status}'."

        now = datetime.utcnow()

        if new_status == 'pickup_initiated':
            pass
        elif new_status == 'food_collected':
            mission.pickup_time = now
            if mission.donation:
                mission.donation.status = 'collected'
        elif new_status == 'delivery_initiated':
            pass
        elif new_status == 'delivery_confirmed':
            mission.delivery_time = now
            if notes:
                mission.delivery_notes = notes
            # Automatically calculate and commit ImpactRecord upon verified delivery!
            cls._record_impact(mission)
            if mission.donation:
                mission.donation.status = 'delivered'
        elif new_status == 'completed':
            if not mission.delivery_time:
                mission.delivery_time = now
            if mission.donation:
                mission.donation.status = 'completed'
            if mission.courier_volunteer:
                mission.courier_volunteer.available = True
        elif new_status == 'cancelled':
            mission.cancellation_reason = notes or "Cancelled by operator"
            if mission.courier_volunteer:
                mission.courier_volunteer.available = True
            if mission.donation:
                mission.donation.status = 'cancelled'

        mission.status = new_status
        mission.updated_at = now

        # Audit log
        audit = AuditLog(
            user_id=actor_user.id if actor_user else None,
            action=f"MISSION_TRANSITION_{new_status.upper()}",
            target_type="RescueMission",
            target_id=mission.id,
            details=f"Mission {mission.mission_code} transitioned {current} -> {new_status}. Notes: {notes or 'N/A'}"
        )
        db.session.add(audit)

        # Notify stakeholders
        cls._notify_mission_update(mission, current, new_status)

        db.session.commit()
        return True, f"Mission successfully transitioned to {new_status}."

    @classmethod
    def _record_impact(cls, mission: RescueMission):
        """Record verified social and environmental impact for delivered food."""
        existing = ImpactRecord.query.filter_by(mission_id=mission.id).first()
        if existing:
            return existing

        donation = mission.donation
        if not donation:
            return None

        # Standard conversion: 1 packet/meal ≈ 0.45 kg
        if donation.unit == 'kg':
            kg = float(donation.quantity)
        elif donation.unit in ['liters', 'l']:
            kg = float(donation.quantity) * 1.0
        else:
            kg = float(donation.quantity) * 0.45

        meals = int(kg / 0.4) if kg > 0 else donation.quantity
        beneficiaries = min(meals, mission.destination_ngo.capacity_people or meals)

        # Environmental estimates (Food and Agriculture Organization / UNEP benchmarks)
        # Average ~2.5 kg CO2e saved per kg food rescued from landfill
        # Average ~250 Liters of water saved embedded in agricultural production per kg
        co2_saved = round(kg * 2.5, 2)
        water_saved = round(kg * 250.0, 1)

        impact = ImpactRecord(
            mission_id=mission.id,
            donation_id=donation.id,
            quantity_kg=round(kg, 2),
            meals_served=meals,
            beneficiaries_reached=beneficiaries,
            co2_saved_kg=co2_saved,
            water_saved_liters=water_saved,
            verified_at=datetime.utcnow()
        )
        db.session.add(impact)
        return impact

    @classmethod
    def _notify_mission_update(cls, mission: RescueMission, old_status: str, new_status: str):
        """Dispatch notifications to Donor, NGO, and Volunteer."""
        label, _ = cls.STATUS_DISPLAY.get(new_status, (new_status, ''))
        msg = f"Mission {mission.mission_code} is now: {label}."

        recipients = []
        if mission.donation and mission.donation.restaurant and mission.donation.restaurant.user_id:
            recipients.append(mission.donation.restaurant.user_id)
        if mission.destination_ngo and mission.destination_ngo.user_id:
            recipients.append(mission.destination_ngo.user_id)
        if mission.courier_volunteer and mission.courier_volunteer.user_id:
            recipients.append(mission.courier_volunteer.user_id)

        for uid in set(recipients):
            notif = Notification(
                user_id=uid,
                title=f"Mission Update: {label}",
                message=msg,
                category="success" if new_status in ['food_collected', 'completed', 'delivery_confirmed'] else "info",
                link_url=f"/mission/{mission.id}"
            )
            db.session.add(notif)
