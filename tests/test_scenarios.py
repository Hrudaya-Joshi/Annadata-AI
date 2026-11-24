"""
ANNADATA AI â€” Automated Test Suite
Validates all 18 core architectural, functional, security, and algorithmic scenarios.
Compatible with both `python -m unittest discover tests` and `pytest`.
"""
import unittest
from datetime import datetime, timedelta, timezone
from app.tools.safety_rules import get_current_time, IST
from app import create_app, db
from app.models import (
    User, Restaurant, NGO, Volunteer, FoodDonation,
    DonationRequest, PickupAssignment, RescueMission,
    ImpactRecord, FoodSafetyAssessment, BeneficiaryDemand
)
from app.agents.food_analysis_agent import FoodAnalysisAgent
from app.agents.ngo_matching_agent import NGOMatchingAgent
from app.agents.coordination_agent import CoordinationAgent
from app.services.allocation_service import AllocationEngine
from app.services.mission_service import MissionService
from app.services.emergency_service import EmergencyRescueService
from app.services.impact_service import ImpactAnalyticsService
from app.services.assistant_service import AssistantService
from app.services.qr_service import QRService


class AnnadataTestSuite(unittest.TestCase):

    def setUp(self):
        self.app = create_app(config_override={
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'WTF_CSRF_ENABLED': False
        })
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _create_sample_entities(self):
        # Restaurant
        u_rest = User(role='restaurant', email='rest@test.com', full_name='Test Chef')
        u_rest.set_password('pass123')
        db.session.add(u_rest)
        db.session.flush()

        rest = Restaurant(
            user_id=u_rest.id,
            business_name='Bistro Alpha',
            food_type='Italian',
            location_address='Indiranagar, Bengaluru',
            latitude=12.9784,
            longitude=77.6408
        )
        db.session.add(rest)

        # NGO
        u_ngo = User(role='ngo', email='ngo@test.com', full_name='NGO Lead')
        u_ngo.set_password('pass123')
        db.session.add(u_ngo)
        db.session.flush()

        ngo = NGO(
            user_id=u_ngo.id,
            organization_name='Shelter Beta',
            food_preferences='cooked meals, vegetarian',
            capacity_people=80,
            location_address='Halasuru, Bengaluru',
            latitude=12.9760,
            longitude=77.6280,
            is_active=True
        )
        db.session.add(ngo)

        # Volunteer
        u_vol = User(role='volunteer', email='vol@test.com', full_name='Courier Gamma')
        u_vol.set_password('pass123')
        db.session.add(u_vol)
        db.session.flush()

        vol = Volunteer(
            user_id=u_vol.id,
            available=True,
            max_distance_km=10.0,
            vehicle_type='bike',
            latitude=12.9750,
            longitude=77.6320
        )
        db.session.add(vol)

        # Admin
        u_admin = User(role='admin', email='admin@test.com', full_name='Admin Delta')
        u_admin.set_password('admin123')
        db.session.add(u_admin)

        db.session.commit()
        return rest, ngo, vol, u_rest, u_ngo, u_vol, u_admin

    # Scenario 1: Restaurant registers and logs in
    def test_01_restaurant_registration_and_login(self):
        res = self.client.post('/register', data={
            'role': 'restaurant',
            'full_name': 'Chef Marco',
            'email': 'marco@restaurant.com',
            'password': 'password123',
            'confirm_password': 'password123',
            'phone': '9876543210',
            'business_name': 'Trattoria Marco',
            'food_type': 'Italian',
            'location_address': 'Koramangala, Bengaluru',
            'latitude': 12.9345,
            'longitude': 77.6265
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        user = User.query.filter_by(email='marco@restaurant.com').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.role, 'restaurant')
        self.assertIsNotNone(user.restaurant)

        # Login
        login_res = self.client.post('/login', data={
            'email': 'marco@restaurant.com',
            'password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)
        self.assertIn(b'Trattoria Marco', login_res.data)

    # Scenario 2: Restaurant submits valid donation
    def test_02_valid_donation_submission(self):
        rest, ngo, vol, u_rest, u_ngo, u_vol, u_admin = self._create_sample_entities()
        self.client.post('/login', data={'email': 'rest@test.com', 'password': 'pass123'})

        now = get_current_time().replace(tzinfo=None)
        res = self.client.post('/restaurant/donate', data={
            'food_name': 'Steamed Rice & Curry',
            'category': 'cooked meals',
            'quantity': '30',
            'unit': 'packets',
            'preparation_time': (now - timedelta(hours=1)).isoformat(),
            'collection_deadline': (now + timedelta(hours=3)).isoformat(),
            'expiry_time': (now + timedelta(hours=5)).isoformat(),
            'storage_temperature': 'Hot Holding (65Â°C)',
            'check_visual': 'on',
            'check_packaging': 'on',
            'check_temp': 'on',
            'check_allergens': 'on',
            'check_hygiene': 'on',
            'temperature_celsius': '65.0'
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        don = FoodDonation.query.filter_by(food_name='Steamed Rice & Curry').first()
        self.assertIsNotNone(don)
        self.assertEqual(don.status, 'suitable')
        self.assertIsNotNone(don.rescue_code)
        self.assertTrue(don.rescue_code.startswith('ANN-RESCUE-'))

    # Scenario 3: Food safety rules validate donation
    def test_03_safety_rules_validation(self):
        rest, _, _, _, _, _, _ = self._create_sample_entities()
        now = get_current_time().replace(tzinfo=None)

        don = FoodDonation(
            restaurant_id=rest.id,
            food_name='Fresh Lentil Soup',
            category='cooked meals',
            quantity=20,
            unit='packets',
            preparation_time=now - timedelta(hours=1),
            expiry_time=now + timedelta(hours=4),
            collection_deadline=now + timedelta(hours=2),
            location_address='Bengaluru',
            latitude=12.97,
            longitude=77.59
        )
        db.session.add(don)
        db.session.commit()

        agent = FoodAnalysisAgent()
        report = agent.run(don.id)
        self.assertTrue(report.get('suitable'))
        self.assertEqual(len(report.get('issues', [])), 0)
        self.assertEqual(don.status, 'suitable')

    # Scenario 4: Invalid or expired food is flagged
    def test_04_expired_food_flagged(self):
        rest, _, _, _, _, _, _ = self._create_sample_entities()
        now = get_current_time().replace(tzinfo=None)

        expired_don = FoodDonation(
            restaurant_id=rest.id,
            food_name='Expired Milk Bottles',
            category='dairy',
            quantity=10,
            unit='liters',
            preparation_time=now - timedelta(hours=48),
            expiry_time=now - timedelta(hours=1),  # Expired
            collection_deadline=now + timedelta(hours=1),
            location_address='Bengaluru',
            latitude=12.97,
            longitude=77.59
        )
        db.session.add(expired_don)
        db.session.commit()

        report = FoodAnalysisAgent().run(expired_don.id)
        self.assertFalse(report.get('suitable'))
        self.assertTrue(len(report.get('issues', [])) > 0)
        self.assertEqual(expired_don.status, 'unsuitable')

    # Scenario 5: AI Category classification / fallback
    def test_05_category_fallback(self):
        agent = FoodAnalysisAgent()
        result = agent.categorize_with_llm("Paneer Butter Masala", "Indian cottage cheese curry")
        self.assertIsNotNone(result)
        # categorize_with_llm now returns (donation_category, sub_category) tuple
        donation_cat, sub_cat = result
        self.assertIn(donation_cat, ["prepared_food", "fresh_produce", "raw_ingredients"])
        self.assertIsNotNone(sub_cat)

    # Scenario 6: NGOs ranked using Smart Allocation Engine (100-pt score)
    def test_06_ngo_smart_allocation_ranking(self):
        rest, ngo, _, _, _, _, _ = self._create_sample_entities()
        now = get_current_time().replace(tzinfo=None)

        don = FoodDonation(
            restaurant_id=rest.id,
            food_name='Sambar Rice',
            category='cooked meals',
            quantity=25,
            unit='packets',
            preparation_time=now - timedelta(hours=1),
            expiry_time=now + timedelta(hours=4),
            collection_deadline=now + timedelta(hours=2),
            location_address='Indiranagar',
            latitude=12.9784,
            longitude=77.6408
        )
        db.session.add(don)
        db.session.commit()

        ranked = AllocationEngine.rank_ngos_for_donation(don)
        self.assertTrue(len(ranked) > 0)
        top = ranked[0]
        self.assertIn('score', top)
        self.assertGreaterEqual(top['score'], 50.0)
        self.assertIn('breakdown', top)
        self.assertIn('distance_score', top['breakdown'])
        self.assertIn('fairness_score', top['breakdown'])

    # Scenario 7: Duplicate matching requests are prevented
    def test_07_prevent_duplicate_requests(self):
        rest, ngo, _, _, _, _, _ = self._create_sample_entities()
        now = get_current_time().replace(tzinfo=None)

        don = FoodDonation(
            restaurant_id=rest.id,
            food_name='Mixed Pulav',
            category='cooked meals',
            quantity=20,
            unit='packets',
            preparation_time=now - timedelta(hours=1),
            expiry_time=now + timedelta(hours=4),
            collection_deadline=now + timedelta(hours=2),
            location_address='Indiranagar',
            latitude=12.9784,
            longitude=77.6408
        )
        db.session.add(don)
        db.session.commit()

        agent = NGOMatchingAgent()
        res1 = agent.run(don.id)
        count1 = DonationRequest.query.filter_by(donation_id=don.id).count()

        # Run matching second time (idempotency check)
        res2 = agent.run(don.id)
        count2 = DonationRequest.query.filter_by(donation_id=don.id).count()
        self.assertEqual(count1, count2)

    # Scenario 8: NGO accepts or rejects request
    def test_08_ngo_accepts_request(self):
        rest, ngo, vol, u_rest, u_ngo, _, _ = self._create_sample_entities()
        now = get_current_time().replace(tzinfo=None)

        don = FoodDonation(
            restaurant_id=rest.id,
            food_name='Chapati & Sabzi',
            category='cooked meals',
            quantity=30,
            unit='packets',
            preparation_time=now - timedelta(hours=1),
            expiry_time=now + timedelta(hours=4),
            collection_deadline=now + timedelta(hours=2),
            location_address='Indiranagar',
            latitude=12.9784,
            longitude=77.6408
        )
        db.session.add(don)
        db.session.flush()

        req = DonationRequest(donation_id=don.id, ngo_id=ngo.id, status='pending')
        db.session.add(req)
        db.session.commit()

        self.client.post('/login', data={'email': 'ngo@test.com', 'password': 'pass123'})
        res = self.client.post(f'/ngo/request/{req.id}/accept', follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        updated_req = DonationRequest.query.get(req.id)
        self.assertEqual(updated_req.status, 'accepted')

        # Verify RescueMission was created
        mission = RescueMission.query.filter_by(donation_id=don.id).first()
        self.assertIsNotNone(mission)

    # Scenario 9: Volunteer assigned correctly
    def test_09_volunteer_assignment(self):
        rest, ngo, vol, _, _, _, _ = self._create_sample_entities()
        now = get_current_time().replace(tzinfo=None)

        don = FoodDonation(
            restaurant_id=rest.id,
            food_name='Dal Tadka',
            category='cooked meals',
            quantity=15,
            unit='packets',
            preparation_time=now - timedelta(hours=1),
            expiry_time=now + timedelta(hours=4),
            collection_deadline=now + timedelta(hours=2),
            location_address='Indiranagar',
            latitude=12.9784,
            longitude=77.6408
        )
        db.session.add(don)
        db.session.commit()

        mission = MissionService.create_mission_for_request(don, ngo, vol)
        self.assertEqual(mission.volunteer_id, vol.id)
        self.assertEqual(mission.status, 'volunteer_assigned')


    # Scenario 10: Volunteer confirms pickup using Kitchen PIN
    def test_10_volunteer_pickup_confirmation(self):
        rest, ngo, vol, _, _, u_vol, _ = self._create_sample_entities()
        now = get_current_time().replace(tzinfo=None)

        don = FoodDonation(
            restaurant_id=rest.id,
            food_name='Pasta Arrabbiata',
            category='cooked meals',
            quantity=20,
            unit='packets',
            preparation_time=now - timedelta(hours=1),
            expiry_time=now + timedelta(hours=4),
            collection_deadline=now + timedelta(hours=2),
            location_address='Indiranagar',
            latitude=12.9784,
            longitude=77.6408
        )
        db.session.add(don)
        db.session.commit()

        mission = MissionService.create_mission_for_request(don, ngo, vol)

        success, msg = MissionService.transition_state(
            mission, 'pickup_initiated', u_vol
        )
        self.assertTrue(success, msg)

        success2, msg2 = MissionService.transition_state(
            mission,
            'food_collected',
            u_vol,
            pin=mission.pickup_pin
        )
        self.assertTrue(success2, msg2)
        self.assertEqual(mission.status, 'food_collected')
        self.assertIsNotNone(mission.pickup_time)

    # Scenario 11: Volunteer starts delivery after verified pickup
    def test_11_volunteer_delivery_initiated(self):
        rest, ngo, vol, _, _, u_vol, _ = self._create_sample_entities()
        now = get_current_time().replace(tzinfo=None)

        don = FoodDonation(
            restaurant_id=rest.id,
            food_name='Idli Vada Sambar',
            category='cooked meals',
            quantity=30,
            unit='packets',
            preparation_time=now - timedelta(hours=1),
            expiry_time=now + timedelta(hours=4),
            collection_deadline=now + timedelta(hours=2),
            location_address='Indiranagar',
            latitude=12.9784,
            longitude=77.6408
        )
        db.session.add(don)
        db.session.commit()

        mission = MissionService.create_mission_for_request(don, ngo, vol)

        success, msg = MissionService.transition_state(
            mission, 'pickup_initiated', u_vol
        )
        self.assertTrue(success, msg)

        success, msg = MissionService.transition_state(
            mission,
            'food_collected',
            u_vol,
            pin=mission.pickup_pin
        )
        self.assertTrue(success, msg)

        success, msg = MissionService.transition_state(
            mission, 'delivery_initiated', u_vol
        )
        self.assertTrue(success, msg)
        self.assertEqual(mission.status, 'delivery_initiated')

    # Scenario 12: Assigned volunteer verifies delivery using Shelter PIN
    def test_12_ngo_verifies_delivery(self):
        rest, ngo, vol, _, u_ngo, u_vol, _ = self._create_sample_entities()
        now = get_current_time().replace(tzinfo=None)

        don = FoodDonation(
            restaurant_id=rest.id,
            food_name='Vegetable Pulao',
            category='cooked meals',
            quantity=25,
            unit='packets',
            preparation_time=now - timedelta(hours=1),
            expiry_time=now + timedelta(hours=4),
            collection_deadline=now + timedelta(hours=2),
            location_address='Indiranagar',
            latitude=12.9784,
            longitude=77.6408
        )
        db.session.add(don)
        db.session.commit()

        mission = MissionService.create_mission_for_request(don, ngo, vol)

        success, msg = MissionService.transition_state(
            mission, 'pickup_initiated', u_vol
        )
        self.assertTrue(success, msg)

        success, msg = MissionService.transition_state(
            mission,
            'food_collected',
            u_vol,
            pin=mission.pickup_pin
        )
        self.assertTrue(success, msg)

        success, msg = MissionService.transition_state(
            mission, 'delivery_initiated', u_vol
        )
        self.assertTrue(success, msg)

        # NGO cannot confirm delivery directly.
        success, msg = MissionService.transition_state(
            mission,
            'delivery_confirmed',
            u_ngo,
            "PIN verified by NGO"
        )
        self.assertFalse(success)
        self.assertEqual(mission.status, 'delivery_initiated')

        # Assigned volunteer confirms delivery using the correct PIN.
        success, msg = MissionService.transition_state(
            mission,
            'delivery_confirmed',
            u_vol,
            "Shelter Delivery PIN verified.",
            pin=mission.verification_pin
        )
        self.assertTrue(success, msg)
        self.assertEqual(mission.status, 'delivery_confirmed')
        self.assertIsNotNone(mission.delivery_time)

    # Scenario 13: Impact metrics update only after verified delivery
    def test_13_impact_metrics_only_on_delivery(self):
        rest, ngo, vol, _, u_ngo, u_vol, _ = self._create_sample_entities()
        now = get_current_time().replace(tzinfo=None)

        don = FoodDonation(
            restaurant_id=rest.id,
            food_name='Fresh Bread Loaves',
            category='baked goods',
            quantity=20,
            unit='pieces',
            preparation_time=now - timedelta(hours=1),
            expiry_time=now + timedelta(hours=24),
            collection_deadline=now + timedelta(hours=4),
            location_address='Indiranagar',
            latitude=12.9784,
            longitude=77.6408
        )
        db.session.add(don)
        db.session.commit()

        impact_before = ImpactAnalyticsService.get_comprehensive_impact()
        initial_kg = impact_before['verified_summary']['total_waste_prevented_kg']

        mission = MissionService.create_mission_for_request(don, ngo, vol)

        # Pending mission should NOT update verified kg.
        impact_pending = ImpactAnalyticsService.get_comprehensive_impact()
        self.assertEqual(
            impact_pending['verified_summary']['total_waste_prevented_kg'],
            initial_kg
        )

        # Start pickup and verify Kitchen PIN.
        success, msg = MissionService.transition_state(
            mission, 'pickup_initiated', u_vol
        )
        self.assertTrue(success, msg)

        success, msg = MissionService.transition_state(
            mission,
            'food_collected',
            u_vol,
            pin=mission.pickup_pin
        )
        self.assertTrue(success, msg)

        # Start delivery.
        success, msg = MissionService.transition_state(
            mission, 'delivery_initiated', u_vol
        )
        self.assertTrue(success, msg)

        # NGO cannot confirm delivery without volunteer PIN verification.
        success, msg = MissionService.transition_state(
            mission, 'delivery_confirmed', u_ngo
        )
        self.assertFalse(success)

        impact_without_verification = ImpactAnalyticsService.get_comprehensive_impact()
        self.assertEqual(
            impact_without_verification['verified_summary']['total_waste_prevented_kg'],
            initial_kg
        )

        # Assigned volunteer verifies the Shelter PIN.
        success, msg = MissionService.transition_state(
            mission,
            'delivery_confirmed',
            u_vol,
            pin=mission.verification_pin
        )
        self.assertTrue(success, msg)

        impact_after = ImpactAnalyticsService.get_comprehensive_impact()
        self.assertGreater(
            impact_after['verified_summary']['total_waste_prevented_kg'],
            initial_kg
        )
        self.assertGreater(
            impact_after['verified_summary']['total_co2_kg'],
            0.0
        )


    # Scenario 14: Emergency alerts trigger correctly
    def test_14_emergency_alert_trigger(self):
        rest, _, _, _, _, _, _ = self._create_sample_entities()
        now = get_current_time().replace(tzinfo=None)

        urgent_don = FoodDonation(
            restaurant_id=rest.id,
            food_name='Hot Vegetable Soup',
            category='cooked meals',
            quantity=15,
            unit='packets',
            preparation_time=now - timedelta(hours=2),
            expiry_time=now + timedelta(hours=2),
            collection_deadline=now + timedelta(minutes=45),  # Within 2 hours
            location_address='Indiranagar',
            latitude=12.9784,
            longitude=77.6408,
            status='suitable'
        )
        db.session.add(urgent_don)
        db.session.commit()

        emergencies = EmergencyRescueService.scan_and_escalate(threshold_hours=2.0)
        self.assertTrue(len(emergencies) > 0)
        found = any(e['donation_id'] == urgent_don.id for e in emergencies)
        self.assertTrue(found)
        self.assertTrue(urgent_don.is_emergency)

    # Scenario 15: QR passport generation and public safe access
    def test_15_qr_passport_public_view(self):
        rest, _, _, _, _, _, _ = self._create_sample_entities()
        now = get_current_time().replace(tzinfo=None)

        don = FoodDonation(
            rescue_code='ANN-RESCUE-202611-9999',
            restaurant_id=rest.id,
            food_name='Fresh Bagels',
            category='baked goods',
            quantity=12,
            unit='pieces',
            preparation_time=now - timedelta(hours=1),
            expiry_time=now + timedelta(hours=24),
            collection_deadline=now + timedelta(hours=4),
            location_address='Koramangala, Bengaluru',
            latitude=12.9345,
            longitude=77.6265,
            status='suitable'
        )
        db.session.add(don)
        db.session.commit()

        res = self.client.get(f'/passport/{don.rescue_code}')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Fresh Bagels', res.data)
        # Verify private phone number is NOT exposed
        self.assertNotIn(b'98450 12345', res.data)

        # SVG route test
        svg_res = self.client.get(f'/passport/{don.rescue_code}/qr.svg')
        self.assertEqual(svg_res.status_code, 200)
        self.assertEqual(svg_res.mimetype, 'image/svg+xml')

    # Scenario 16: Role authorization and protection
    def test_16_role_access_protection(self):
        _, _, _, u_rest, u_ngo, u_vol, _ = self._create_sample_entities()

        # Volunteer attempting to access restaurant dashboard
        self.client.post('/login', data={'email': 'vol@test.com', 'password': 'pass123'})
        res = self.client.get('/restaurant/dashboard', follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        # Should redirect to home with flash access denied
        self.assertIn(b'Access denied', res.data)

        # NGO attempting to access admin dashboard
        self.client.post('/login', data={'email': 'ngo@test.com', 'password': 'pass123'})
        admin_res = self.client.get('/admin/dashboard', follow_redirects=True)
        self.assertIn(b'Administrator access required', admin_res.data)

    # Scenario 17: AI Assistant respects role permissions
    def test_17_assistant_role_scoping(self):
        _, _, _, u_rest, u_ngo, _, _ = self._create_sample_entities()

        # Restaurant asks question
        resp_rest = AssistantService.chat(u_rest, "Show my donation performance")
        self.assertEqual(resp_rest['role'], 'restaurant')
        self.assertIn('Total Donations Created', resp_rest['answer'])

        # NGO asks question
        resp_ngo = AssistantService.chat(u_ngo, "What is our capacity status?")
        self.assertEqual(resp_ngo['role'], 'ngo')
        self.assertIn('Capacity Overview', resp_ngo['answer'])

    # Scenario 18: Application runs cleanly without an AI API key
    def test_18_runs_without_api_key(self):
        _, _, _, u_rest, _, _, _ = self._create_sample_entities()
        # Verify assistant produces complete deterministic response when offline / no API key
        resp = AssistantService.chat(u_rest, "When should I donate surplus food?")
        self.assertIsNotNone(resp['answer'])
        self.assertIn('Peak Timing', resp['answer'])
        self.assertEqual(resp['source'], "Annadata Deterministic Engine (Offline / Local Mode)")


if __name__ == '__main__':
    unittest.main()
