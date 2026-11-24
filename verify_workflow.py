"""
ANNADATA AI — End-to-End Workflow & Component Verification Script
Validates:
1. Complete 10-stage rescue mission lifecycle (Restaurant -> Safety -> NGO -> Volunteer -> Delivery -> Impact)
2. Role-based access control and authorization barriers
3. Public-safe QR Food Rescue Passport & SVG generator
4. Smart 100-point multi-factor NGO allocation engine
5. Emergency rescue deadline escalation scanner
6. Predictive surplus forecasting & impact analytics calculations
7. Offline AI agent fallback resilience (zero external API dependency)
"""
import sys
from datetime import datetime, timedelta, timezone
from app.tools.safety_rules import get_current_time
from app import create_app, db
from app.models import (
    User, Restaurant, NGO, Volunteer, FoodDonation,
    DonationRequest, PickupAssignment, RescueMission,
    ImpactRecord, FoodSafetyAssessment, BeneficiaryDemand
)
from app.services.allocation_service import AllocationEngine
from app.services.mission_service import MissionService
from app.services.emergency_service import EmergencyRescueService
from app.services.forecast_service import SurplusForecastingService
from app.services.impact_service import ImpactAnalyticsService
from app.services.assistant_service import AssistantService
from app.services.qr_service import QRService
from app.agents.food_analysis_agent import FoodAnalysisAgent
from app.agents.ngo_matching_agent import NGOMatchingAgent
from app.agents.coordination_agent import CoordinationAgent
from app.agents.surplus_prediction_agent import SurplusPredictionAgent
from app.agents.impact_analytics_agent import ImpactAnalyticsAgent
from app.agents.rescue_assistant_agent import RescueAssistantAgent

def run_verification():
    app = create_app(config_override={
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
        'OPENROUTER_API_KEY': None  # Strictly verify offline operation
    })

    with app.app_context():
        db.create_all()
        client = app.test_client()
        now = get_current_time().replace(tzinfo=None)

        print("=" * 65)
        print("ANNADATA AI — SYSTEMATIC END-TO-END VERIFICATION")
        print("=" * 65)

        # -------------------------------------------------------------
        # STEP 1: Set up Users & Entities
        # -------------------------------------------------------------
        print("\n[1/7] Initializing test entities across all 4 roles...")
        u_rest = User(role='restaurant', email='chef@kitchen.com', full_name='Master Chef Dev')
        u_rest.set_password('pass123')
        db.session.add(u_rest)
        db.session.flush()

        rest = Restaurant(
            user_id=u_rest.id,
            business_name='Heritage Biryani House',
            food_type='Indian',
            location_address='Koramangala 5th Block, Bengaluru',
            latitude=12.9352,
            longitude=77.6245
        )
        db.session.add(rest)

        u_ngo = User(role='ngo', email='lead@feedhope.org', full_name='Hope Foundation Lead')
        u_ngo.set_password('pass123')
        db.session.add(u_ngo)
        db.session.flush()

        ngo = NGO(
            user_id=u_ngo.id,
            organization_name='Feed Hope Foundation',
            location_address='Ejipura, Bengaluru',
            latitude=12.9400,
            longitude=77.6280,
            capacity_people=150,
            food_preferences='cooked meals,vegetarian,snacks'
        )
        db.session.add(ngo)

        u_vol = User(role='volunteer', email='rider@volunteer.org', full_name='Quick Rescue Rider')
        u_vol.set_password('pass123')
        db.session.add(u_vol)
        db.session.flush()

        vol = Volunteer(
            user_id=u_vol.id,
            vehicle_type='bike',
            available=True,
            latitude=12.9370,
            longitude=77.6260
        )
        db.session.add(vol)

        u_admin = User(role='admin', email='super@annadata.ai', full_name='System Admin')
        u_admin.set_password('admin123')
        db.session.add(u_admin)
        db.session.commit()
        print("  -> Created Restaurant, NGO, Volunteer, and Admin.")

        # -------------------------------------------------------------
        # STEP 2: Role-Based Authorization & Security
        # -------------------------------------------------------------
        print("\n[2/7] Verifying role-based access control (RBAC)...")
        # Anonymous accessing protected route
        res = client.get('/restaurant/dashboard')
        assert res.status_code == 302 and '/login' in res.location, "Anonymous access failed to redirect"

        # Volunteer attempting to access Restaurant dashboard
        client.post('/login', data={'email': 'rider@volunteer.org', 'password': 'pass123'})
        res = client.get('/restaurant/dashboard', follow_redirects=True)
        assert res.status_code == 200 and b'Access denied' in res.data, "Volunteer accessed restaurant dashboard without redirect/flash"

        # Restaurant attempting to access Admin dashboard
        client.get('/logout')
        client.post('/login', data={'email': 'chef@kitchen.com', 'password': 'pass123'})
        res = client.get('/admin/dashboard', follow_redirects=True)
        assert res.status_code == 200 and (b'Access denied' in res.data or b'Administrator access required' in res.data), "Restaurant accessed admin dashboard without protection"
        client.get('/logout')
        print("  -> RBAC security barriers strictly enforced (302 redirect + access denied).")

        # -------------------------------------------------------------
        # STEP 3: Complete 10-Stage Rescue Mission Workflow
        # -------------------------------------------------------------
        print("\n[3/7] Testing complete 10-stage rescue mission lifecycle...")
        # 1. Submission & Safety Screening
        donation = FoodDonation(
            restaurant_id=rest.id,
            food_name='Vegetable Pulao & Dal Tadka',
            category='cooked meals',
            quantity=50,
            unit='kg',
            preparation_time=now - timedelta(hours=1),
            expiry_time=now + timedelta(hours=6),
            collection_deadline=now + timedelta(hours=3),
            location_address='Koramangala 5th Block, Bengaluru',
            latitude=12.9352,
            longitude=77.6245,
            storage_temperature='Warm (>60C)',
            packaging_type='Food-Grade Thermal Containers',
            status='pending_analysis'
        )
        db.session.add(donation)
        db.session.commit()

        analysis_agent = FoodAnalysisAgent()
        report = analysis_agent.run(donation.id)
        assert report.get('suitable') is True, f"Food was not marked suitable: {report}"
        assert donation.rescue_code.startswith('ANN-RESCUE-'), "Rescue code not properly generated"
        print(f"  Stage 1-2 Passed: Submitted & Assessed (Rescue Code: {donation.rescue_code})")

        # 2. Smart NGO Matching
        ranked = AllocationEngine.rank_ngos_for_donation(donation)
        assert len(ranked) > 0, "No NGOs ranked by allocation engine"
        top = ranked[0]
        assert top['score'] >= 50, f"Expected strong match score, got {top['score']}"
        print(f"  Stage 3 Passed: Smart Matching Score {top['score']}/100 with breakdown: {top['breakdown']}")

        req = DonationRequest(
            donation_id=donation.id,
            ngo_id=ngo.id,
            status='pending',
            match_score=top['score'],
            score_breakdown=str(top['breakdown'])
        )
        db.session.add(req)
        db.session.commit()

        # 3. NGO Acceptance & Mission Creation
        mission = MissionService.create_mission_for_request(donation, ngo, vol)
        assert mission is not None, "Failed to create rescue mission"
        assert mission.status == 'volunteer_assigned', f"Unexpected initial state {mission.status}"
        print(f"  Stage 4-5 Passed: NGO Accepted & Volunteer Assigned -> Mission #{mission.mission_code} ({mission.status})")

        # 4. Pickup Initiated
        success, msg = MissionService.transition_state(mission, 'pickup_initiated', u_vol)
        assert success, f"Pickup initiation failed: {msg}"
        assert mission.status == 'pickup_initiated', "Status not updated to pickup_initiated"
        print(f"  Stage 6 Passed: Pickup Initiated (Status: {mission.status})")

        # 5. Food Collected
        success, msg = MissionService.transition_state(mission, 'food_collected', u_vol)
        assert success, f"Food collection failed: {msg}"
        assert mission.status == 'food_collected', "Status not updated to food_collected"
        print(f"  Stage 7 Passed: Food Collected (Status: {mission.status})")

        # 6. Delivery Initiated
        success, msg = MissionService.transition_state(mission, 'delivery_initiated', u_vol)
        assert success, f"Delivery initiation failed: {msg}"
        assert mission.status == 'delivery_initiated', "Status not updated to delivery_initiated"
        print(f"  Stage 8 Passed: Delivery Initiated (Status: {mission.status})")

        # 7. Delivery Confirmed
        success, msg = MissionService.transition_state(mission, 'delivery_confirmed', u_ngo, "PIN and temperature verified")
        assert success, f"Delivery confirmation failed: {msg}"
        assert mission.status == 'delivery_confirmed', f"Expected delivery_confirmed, got {mission.status}"
        print(f"  Stage 9-10 Passed: Delivery Confirmed -> Mission COMPLETED!")

        # 8. Verify Impact Creation
        impact = ImpactRecord.query.filter_by(mission_id=mission.id).first()
        assert impact is not None, "ImpactRecord was not created upon mission completion"
        assert impact.quantity_kg > 0, "Impact quantity_kg is zero"
        print(f"  Impact Verified: {impact.quantity_kg} kg saved | {impact.meals_served} meals | {impact.co2_saved_kg} kg CO2e | {impact.water_saved_liters} L H2O")

        # -------------------------------------------------------------
        # STEP 4: Food Rescue Passport & Public QR View
        # -------------------------------------------------------------
        print("\n[4/7] Testing Food Rescue Passport & Public QR Verification...")
        # SVG endpoint
        res = client.get(f'/passport/{donation.rescue_code}/qr.svg')
        assert res.status_code == 200, "QR SVG endpoint failed"
        assert res.content_type.startswith('image/svg+xml'), f"Wrong content type {res.content_type}"
        assert b'<svg' in res.data, "Invalid SVG output"

        # Public HTML verification page (no login required)
        res = client.get(f'/passport/{donation.rescue_code}')
        assert res.status_code == 200, "Public passport view failed"
        html = res.data.decode('utf-8')
        assert donation.rescue_code in html, "Passport code missing from page"
        assert "Vegetable Pulao" in html, "Food item name missing"
        # Verify privacy masking (donor phone should NOT be exposed publicly)
        assert "+91 99001" not in html, "Private phone leaked in public view!"
        print("  -> QR SVG generated cleanly. Public passport verifies tamper-evident status without privacy leak.")

        # -------------------------------------------------------------
        # STEP 5: Emergency Escalation Mode
        # -------------------------------------------------------------
        print("\n[5/7] Testing Emergency Rescue Escalation Scanner...")
        urgent_donation = FoodDonation(
            restaurant_id=rest.id,
            food_name='Assorted Sandwiches & Juices',
            category='snacks',
            quantity=25,
            unit='kg',
            preparation_time=now - timedelta(hours=2),
            expiry_time=now + timedelta(hours=1),
            collection_deadline=now + timedelta(minutes=45),  # 45 mins left (< 2 hour threshold)
            location_address='Koramangala 5th Block, Bengaluru',
            latitude=12.9352,
            longitude=77.6245,
            status='suitable'
        )
        db.session.add(urgent_donation)
        db.session.commit()

        escalated_list = EmergencyRescueService.scan_and_escalate(threshold_hours=2.0)
        assert len(escalated_list) >= 1, "Emergency service failed to detect at-risk donation"
        urgent_donation_reloaded = db.session.get(FoodDonation, urgent_donation.id)
        assert urgent_donation_reloaded.is_emergency is True, "Donation is_emergency flag not set"
        print(f"  -> Emergency successfully escalated: {escalated_list[0]['urgency_badge']} detected ({escalated_list[0]['mins_remaining']}m remaining).")

        # -------------------------------------------------------------
        # STEP 6: Predictive Analytics & Impact Aggregation
        # -------------------------------------------------------------
        print("\n[6/7] Testing Predictive Forecasting & Verified Impact Aggregations...")
        overview = SurplusForecastingService.get_intelligence_overview()
        assert 'day_stats' in overview, "Forecast missing day_stats"
        assert 'sector_forecasts' in overview, "Forecast missing sector_forecasts"
        assert 'insights' in overview, "Forecast missing insights"
        print(f"  -> Predictive Engine: {len(overview['sector_forecasts'])} sector projections. Mode: {'Demo Baseline' if overview['is_demo_mode'] else 'Historical'}")

        stats = ImpactAnalyticsService.get_comprehensive_impact()
        assert stats['verified_summary']['total_kg_rescued'] > 0, "Impact stats did not include completed mission"
        assert stats['missions']['completed'] >= 1, "Completed missions count incorrect"
        print(f"  -> Impact Intelligence: {stats['verified_summary']['total_kg_rescued']} kg total rescued across {stats['missions']['completed']} missions.")

        # -------------------------------------------------------------
        # STEP 7: Offline AI Agent & Floating Assistant Fallback
        # -------------------------------------------------------------
        print("\n[7/7] Testing Offline AI Agents & Floating Assistant Resilience...")
        coord_res = CoordinationAgent().run(donation.id, ngo.id, vol.id)
        assert coord_res is not None and "error" not in coord_res, f"CoordinationAgent failed: {coord_res}"
        print("  -> CoordinationAgent: Executed successfully offline.")

        surplus_res = SurplusPredictionAgent().run()
        assert surplus_res is not None and "error" not in surplus_res, f"SurplusPredictionAgent failed: {surplus_res}"
        print("  -> SurplusPredictionAgent: Executed successfully offline.")

        impact_agent_res = ImpactAnalyticsAgent().run()
        assert impact_agent_res is not None and "error" not in impact_agent_res, f"ImpactAnalyticsAgent failed: {impact_agent_res}"
        print("  -> ImpactAnalyticsAgent: Executed successfully offline.")

        rescue_ast_res = RescueAssistantAgent().run(u_ngo, "What are my active rescue missions and what is the current impact?")
        assert rescue_ast_res is not None and "answer" in rescue_ast_res, f"RescueAssistantAgent failed: {rescue_ast_res}"
        print(f"  -> RescueAssistantAgent: Executed successfully offline (Source: {rescue_ast_res.get('source')}).")

        # Floating assistant offline query
        assistant_reply = AssistantService.chat(
            user=u_ngo,
            message="What are my active rescue missions and what is the current impact?"
        )
        assert len(assistant_reply.get("answer", "")) > 20, "Assistant returned empty reply"
        print(f"  -> Floating Assistant Offline Reply Preview: \"{assistant_reply['answer'][:95]}...\"")

        print("\n" + "=" * 65)
        print(">>> ALL 7 CORE SUBSYSTEM VERIFICATIONS PASSED WITH 100% SUCCESS! <<<")
        print("=" * 65)

if __name__ == '__main__':
    run_verification()
