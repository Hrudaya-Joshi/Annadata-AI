"""
ANNADATA AI — Seed Data Generation Script
Populates the database with realistic demonstration accounts, verified donations,
tracked rescue missions, and benchmark impact metrics for academic & viva evaluation.

Run with: python -m seeds.sample_data
"""
from datetime import datetime, timedelta, timezone
from app import create_app, db
from app.models import (
    User, Restaurant, NGO, Volunteer, FoodDonation, FoodSafetyAssessment,
    DonationRequest, PickupAssignment, RescueMission, ImpactRecord,
    BeneficiaryDemand, Notification, AuditLog, AgentExecutionLog
)
from app.services.qr_service import QRService


def create_sample_data():
    app = create_app()

    with app.app_context():
        print("Clearing and rebuilding ANNADATA AI database schema...")
        db.drop_all()
        db.create_all()

        now = datetime.now(timezone.utc).replace(tzinfo=None)

        print("1. Creating role-based user accounts...")
        # 1. Primary Restaurant
        rest_user = User(
            role='restaurant',
            email='restaurant@example.com',
            full_name='Chef Vikram Oberoi',
            phone='+91 98450 12345',
            is_active=True
        )
        rest_user.set_password('password123')
        db.session.add(rest_user)
        db.session.flush()

        restaurant1 = Restaurant(
            user_id=rest_user.id,
            business_name='Golden Spoon Banquet & Bistro',
            food_type='North & South Indian Multi-Cuisine',
            location_address='123 100-Ft Road, Indiranagar, Bengaluru',
            latitude=12.9784,
            longitude=77.6408
        )
        db.session.add(restaurant1)

        # 2. Second Restaurant
        rest2_user = User(
            role='restaurant',
            email='bistro@example.com',
            full_name='Chef Ananya Sen',
            phone='+91 98450 67890',
            is_active=True
        )
        rest2_user.set_password('password123')
        db.session.add(rest2_user)
        db.session.flush()

        restaurant2 = Restaurant(
            user_id=rest2_user.id,
            business_name='Green Leaf Organic Cafe',
            food_type='Continental & Healthy Bowls',
            location_address='45 80-Ft Road, Koramangala 4th Block, Bengaluru',
            latitude=12.9345,
            longitude=77.6265
        )
        db.session.add(restaurant2)

        # 3. Primary NGO
        ngo_user = User(
            role='ngo',
            email='ngo@example.com',
            full_name='Sister Mary Verghese',
            phone='+91 98451 11223',
            is_active=True
        )
        ngo_user.set_password('password123')
        db.session.add(ngo_user)
        db.session.flush()

        ngo1 = NGO(
            user_id=ngo_user.id,
            organization_name='Helping Hands Community Shelter',
            registration_number='NGO/BLR/2024/0981',
            food_preferences='vegetarian, cooked meals, fruits, baked goods',
            capacity_people=120,
            location_address='56 Halasuru Main Road, Bengaluru',
            latitude=12.9760,
            longitude=77.6280,
            is_active=True
        )
        db.session.add(ngo1)

        # 4. Second NGO
        ngo2_user = User(
            role='ngo',
            email='shelter@example.com',
            full_name='Dr. Ramesh Kulkarni',
            phone='+91 98452 33445',
            is_active=True
        )
        ngo2_user.set_password('password123')
        db.session.add(ngo2_user)
        db.session.flush()

        ngo2 = NGO(
            user_id=ngo2_user.id,
            organization_name='Aashraya Orphanage & Senior Center',
            registration_number='NGO/BLR/2023/1142',
            food_preferences='cooked meals, vegetarian, dairy, fruits',
            capacity_people=80,
            location_address='12 Ejipura Ring Road, Bengaluru',
            latitude=12.9410,
            longitude=77.6295,
            is_active=True
        )
        db.session.add(ngo2)

        # 5. Primary Volunteer
        vol_user = User(
            role='volunteer',
            email='volunteer@example.com',
            full_name='Kavya Krishnan',
            phone='+91 98453 55667',
            is_active=True
        )
        vol_user.set_password('password123')
        db.session.add(vol_user)
        db.session.flush()

        volunteer1 = Volunteer(
            user_id=vol_user.id,
            available=True,
            max_distance_km=15.0,
            vehicle_type='bike',
            latitude=12.9750,
            longitude=77.6320
        )
        db.session.add(volunteer1)

        # 6. Second Volunteer
        vol2_user = User(
            role='volunteer',
            email='courier@example.com',
            full_name='Arjun Nair',
            phone='+91 98454 77889',
            is_active=True
        )
        vol2_user.set_password('password123')
        db.session.add(vol2_user)
        db.session.flush()

        volunteer2 = Volunteer(
            user_id=vol2_user.id,
            available=True,
            max_distance_km=10.0,
            vehicle_type='scooter',
            latitude=12.9380,
            longitude=77.6210
        )
        db.session.add(volunteer2)

        # 7. System Admin
        admin_user = User(
            role='admin',
            email='admin@example.com',
            full_name='System Architect (Admin)',
            phone='+91 98455 99000',
            is_active=True
        )
        admin_user.set_password('admin123')
        db.session.add(admin_user)
        db.session.commit()

        print("2. Creating realistic food donations and safety assessments...")
        # Donation 1: Delivered & Verified (Cooked Meal)
        don1 = FoodDonation(
            rescue_code='ANN-RESCUE-202611-1001',
            restaurant_id=restaurant1.id,
            food_name='Vegetable Dum Biryani & Mirchi Ka Salan',
            category='cooked meals',
            quantity=40,
            unit='packets',
            preparation_time=now - timedelta(hours=6),
            expiry_time=now + timedelta(hours=2),
            collection_deadline=now - timedelta(hours=3),
            description='Freshly packed aromatic vegetable biryani in sealed meal containers with raita.',
            location_address=restaurant1.location_address,
            latitude=restaurant1.latitude,
            longitude=restaurant1.longitude,
            status='delivered',
            suitability_score=96.0,
            analysis_report='{"suitable": true, "issues": [], "risk_level": "low"}',
            storage_temperature='Hot Holding (68°C)',
            dietary_flags='Vegetarian, Nut-Free',
            packaging_type='Food-grade sealed thermal foil trays',
            created_at=now - timedelta(hours=6)
        )
        db.session.add(don1)
        db.session.flush()

        safe1 = FoodSafetyAssessment(
            donation_id=don1.id,
            visual_inspection_passed=True,
            packaging_intact=True,
            temperature_controlled=True,
            allergens_declared=True,
            hygiene_verified=True,
            temperature_celsius=68.0,
            risk_level='low',
            ai_risk_observations='Optimal thermal holding verified. Zero hygiene deviations.',
            verified_by_user_id=rest_user.id,
            verified_at=now - timedelta(hours=6)
        )
        db.session.add(safe1)

        # Donation 2: Active In-Transit Mission
        don2 = FoodDonation(
            rescue_code='ANN-RESCUE-202611-1002',
            restaurant_id=restaurant2.id,
            food_name='Artisanal Multigrain Sourdough Loaves',
            category='baked goods',
            quantity=25,
            unit='pieces',
            preparation_time=now - timedelta(hours=2),
            expiry_time=now + timedelta(hours=24),
            collection_deadline=now + timedelta(hours=2),
            description='Crusty sourdough breads baked this morning. Sealed in food-safe paper bags.',
            location_address=restaurant2.location_address,
            latitude=restaurant2.latitude,
            longitude=restaurant2.longitude,
            status='matched',
            suitability_score=98.0,
            analysis_report='{"suitable": true, "issues": [], "risk_level": "low"}',
            storage_temperature='Room Temperature',
            dietary_flags='Vegan, Dairy-Free',
            packaging_type='Sanitized craft paper sleeves',
            created_at=now - timedelta(hours=2)
        )
        db.session.add(don2)
        db.session.flush()

        safe2 = FoodSafetyAssessment(
            donation_id=don2.id,
            visual_inspection_passed=True,
            packaging_intact=True,
            temperature_controlled=True,
            allergens_declared=True,
            hygiene_verified=True,
            temperature_celsius=24.0,
            risk_level='low',
            ai_risk_observations='Baked goods dry storage compliance verified.',
            verified_by_user_id=rest2_user.id,
            verified_at=now - timedelta(hours=2)
        )
        db.session.add(safe2)

        # Donation 3: Emergency Rescue Mode (Approaching deadline in 45 mins!)
        don3 = FoodDonation(
            rescue_code='ANN-RESCUE-202611-1003',
            restaurant_id=restaurant1.id,
            food_name='Paneer Butter Masala & Tandoori Rotis',
            category='cooked meals',
            quantity=30,
            unit='packets',
            preparation_time=now - timedelta(hours=3),
            expiry_time=now + timedelta(hours=2),
            collection_deadline=now + timedelta(minutes=45),  # 45 mins remaining -> Emergency!
            description='Warm paneer curry and soft wheat rotis from lunch banquet.',
            location_address=restaurant1.location_address,
            latitude=restaurant1.latitude,
            longitude=restaurant1.longitude,
            status='suitable',
            is_emergency=True,
            suitability_score=92.0,
            analysis_report='{"suitable": true, "issues": [], "risk_level": "low"}',
            storage_temperature='Hot Holding (64°C)',
            dietary_flags='Vegetarian',
            packaging_type='Heat-sealed plastic trays',
            created_at=now - timedelta(hours=3)
        )
        db.session.add(don3)
        db.session.flush()

        safe3 = FoodSafetyAssessment(
            donation_id=don3.id,
            visual_inspection_passed=True,
            packaging_intact=True,
            temperature_controlled=True,
            allergens_declared=True,
            hygiene_verified=True,
            temperature_celsius=64.0,
            risk_level='low',
            ai_risk_observations='Approaching urgency threshold. Rapid dispatch recommended.',
            verified_by_user_id=rest_user.id,
            verified_at=now - timedelta(hours=3)
        )
        db.session.add(safe3)

        # Donation 4: Flagged Unsuitable (Expired food demonstration)
        don4 = FoodDonation(
            rescue_code='ANN-RESCUE-202611-1004',
            restaurant_id=restaurant2.id,
            food_name='Fresh Cream Pastries (Expired)',
            category='dairy',
            quantity=12,
            unit='packets',
            preparation_time=now - timedelta(hours=48),
            expiry_time=now - timedelta(hours=2),  # Expired 2 hours ago!
            collection_deadline=now - timedelta(hours=1),
            description='Dairy cream pastries left at ambient counter temperature.',
            location_address=restaurant2.location_address,
            latitude=restaurant2.latitude,
            longitude=restaurant2.longitude,
            status='unsuitable',
            suitability_score=0.0,
            analysis_report='{"suitable": false, "issues": ["Food is expired or expiry time is missing."], "risk_level": "critical"}',
            storage_temperature='Unrefrigerated',
            dietary_flags='Contains Dairy, Egg',
            packaging_type='Cardboard box',
            created_at=now - timedelta(hours=1)
        )
        db.session.add(don4)
        db.session.flush()

        safe4 = FoodSafetyAssessment(
            donation_id=don4.id,
            visual_inspection_passed=False,
            packaging_intact=True,
            temperature_controlled=False,
            allergens_declared=True,
            hygiene_verified=False,
            temperature_celsius=26.5,
            risk_level='critical',
            ai_risk_observations='BLOCK: Expiry threshold violated. Bacterial growth risk on ambient cream.',
            verified_by_user_id=rest2_user.id,
            verified_at=now - timedelta(hours=1)
        )
        db.session.add(safe4)

        # Donation 5: Healthy Produce & Fruits
        don5 = FoodDonation(
            rescue_code='ANN-RESCUE-202611-1005',
            restaurant_id=restaurant2.id,
            food_name='Fresh Organic Apples & Oranges Basket',
            category='fruits',
            quantity=18,
            unit='kg',
            preparation_time=now - timedelta(hours=4),
            expiry_time=now + timedelta(days=3),
            collection_deadline=now + timedelta(hours=5),
            description='Surplus whole organic apples and sweet oranges from juice bar prep.',
            location_address=restaurant2.location_address,
            latitude=restaurant2.latitude,
            longitude=restaurant2.longitude,
            status='suitable',
            suitability_score=99.0,
            analysis_report='{"suitable": true, "issues": [], "risk_level": "low"}',
            storage_temperature='Ambient Cool',
            dietary_flags='Vegan, Raw Produce',
            packaging_type='Wooden fruit crates',
            created_at=now - timedelta(hours=4)
        )
        db.session.add(don5)
        db.session.commit()

        print("3. Creating donation requests and tracked rescue missions...")
        # Request & Mission 1: Completed & Delivered
        req1 = DonationRequest(
            donation_id=don1.id,
            ngo_id=ngo1.id,
            status='accepted',
            distance_km=1.85,
            match_score=96.5,
            score_breakdown='{"distance_score": 25.0, "category_score": 25.0, "capacity_score": 20.0, "demand_score": 15.0, "volunteer_score": 5.0, "fairness_score": 6.5}',
            requested_at=now - timedelta(hours=5, minutes=45),
            responded_at=now - timedelta(hours=5, minutes=30),
            response_notes='Accepted immediately for shelter evening meal.'
        )
        db.session.add(req1)
        db.session.flush()

        assign1 = PickupAssignment(
            request_id=req1.id,
            volunteer_id=volunteer1.id,
            status='delivered',
            assigned_at=now - timedelta(hours=5, minutes=30),
            accepted_at=now - timedelta(hours=5, minutes=20),
            picked_up_at=now - timedelta(hours=4, minutes=45),
            delivered_at=now - timedelta(hours=4, minutes=10),
            notes='Delivered in insulated food carriers. Handover confirmed.'
        )
        db.session.add(assign1)

        mission1 = RescueMission(
            mission_code='ANN-MSN-202611-001',
            donation_id=don1.id,
            ngo_id=ngo1.id,
            volunteer_id=volunteer1.id,
            status='delivery_confirmed',
            pickup_deadline=don1.collection_deadline,
            delivery_deadline=don1.collection_deadline + timedelta(hours=1),
            pickup_time=now - timedelta(hours=4, minutes=45),
            delivery_time=now - timedelta(hours=4, minutes=10),
            verification_pin='839104',
            delivery_notes='Handover verified by Sister Mary. Temperature at arrival: 63°C.',
            created_at=now - timedelta(hours=5, minutes=30),
            updated_at=now - timedelta(hours=4, minutes=10)
        )
        db.session.add(mission1)
        db.session.flush()

        # Verified Social & Environmental Impact Record
        impact1 = ImpactRecord(
            mission_id=mission1.id,
            donation_id=don1.id,
            quantity_kg=18.0,  # 40 packets * 0.45 kg
            meals_served=45,
            beneficiaries_reached=40,
            co2_saved_kg=45.0,  # 18 * 2.5 kg
            water_saved_liters=4500.0,  # 18 * 250 L
            verified_at=now - timedelta(hours=4, minutes=10)
        )
        db.session.add(impact1)

        # Request & Mission 2: Active In-Transit
        req2 = DonationRequest(
            donation_id=don2.id,
            ngo_id=ngo2.id,
            status='accepted',
            distance_km=1.2,
            match_score=94.0,
            score_breakdown='{"distance_score": 25.0, "category_score": 25.0, "capacity_score": 20.0, "demand_score": 10.0, "volunteer_score": 5.0, "fairness_score": 9.0}',
            requested_at=now - timedelta(hours=1, minutes=45),
            responded_at=now - timedelta(hours=1, minutes=30),
            response_notes='Accepted for breakfast bread distribution.'
        )
        db.session.add(req2)
        db.session.flush()

        assign2 = PickupAssignment(
            request_id=req2.id,
            volunteer_id=volunteer2.id,
            status='picked_up',
            assigned_at=now - timedelta(hours=1, minutes=30),
            accepted_at=now - timedelta(hours=1, minutes=20),
            picked_up_at=now - timedelta(minutes=30),
            notes='Collected from bakery. Heading to Aashraya shelter.'
        )
        db.session.add(assign2)
        volunteer2.available = False

        mission2 = RescueMission(
            mission_code='ANN-MSN-202611-002',
            donation_id=don2.id,
            ngo_id=ngo2.id,
            volunteer_id=volunteer2.id,
            status='food_collected',
            pickup_deadline=don2.collection_deadline,
            delivery_deadline=don2.collection_deadline + timedelta(hours=1),
            pickup_time=now - timedelta(minutes=30),
            verification_pin='492716',
            created_at=now - timedelta(hours=1, minutes=30),
            updated_at=now - timedelta(minutes=30)
        )
        db.session.add(mission2)

        # Request 3: Pending review for Emergency Donation 3
        req3 = DonationRequest(
            donation_id=don3.id,
            ngo_id=ngo1.id,
            status='pending',
            distance_km=2.1,
            match_score=91.0,
            score_breakdown='{"distance_score": 25.0, "category_score": 25.0, "capacity_score": 18.0, "demand_score": 15.0, "volunteer_score": 5.0, "fairness_score": 3.0}',
            requested_at=now - timedelta(hours=2, minutes=50)
        )
        db.session.add(req3)

        print("4. Creating community beneficiary demands & notifications...")
        demand1 = BeneficiaryDemand(
            ngo_id=ngo1.id,
            category='cooked meals',
            required_quantity=60,
            urgency_level='urgent',
            notes='Shelter resident dinner meal shortage.',
            created_at=now - timedelta(hours=8)
        )
        demand2 = BeneficiaryDemand(
            ngo_id=ngo2.id,
            category='baked goods',
            required_quantity=30,
            urgency_level='normal',
            notes='Breakfast rolls for children.',
            created_at=now - timedelta(hours=12)
        )
        db.session.add(demand1)
        db.session.add(demand2)

        notif1 = Notification(
            user_id=ngo_user.id,
            title='URGENT: Emergency Food Rescue Alert',
            message='Donation #3 (Paneer Butter Masala) collection deadline is within 45 minutes.',
            category='urgent',
            link_url='/ngo/dashboard',
            is_read=False,
            created_at=now - timedelta(minutes=30)
        )
        notif2 = Notification(
            user_id=rest_user.id,
            title='Rescue Mission Completed!',
            message='Mission ANN-MSN-202611-001 has been safely delivered to Helping Hands Community Shelter.',
            category='success',
            link_url='/restaurant/dashboard',
            is_read=True,
            created_at=now - timedelta(hours=4)
        )
        db.session.add(notif1)
        db.session.add(notif2)

        audit1 = AuditLog(
            user_id=admin_user.id,
            action='SYSTEM_INITIALIZATION',
            target_type='Database',
            details='ANNADATA AI production seed protocol initialized successfully.',
            created_at=now - timedelta(days=1)
        )
        db.session.add(audit1)

        agent_log1 = AgentExecutionLog(
            donation_id=don1.id,
            agent_name='FoodAnalysisAgent',
            task='analyze',
            input_data='{"donation_id": 1, "food_name": "Vegetable Dum Biryani"}',
            output_data='{"suitable": true, "issues": [], "suitability_score": 96.0}',
            status='success',
            created_at=now - timedelta(hours=6)
        )
        agent_log2 = AgentExecutionLog(
            donation_id=don1.id,
            agent_name='NGOMatchingAgent',
            task='match',
            input_data='{"donation_id": 1}',
            output_data='{"top_match": "Helping Hands Community Shelter", "score": 96.5}',
            status='success',
            created_at=now - timedelta(hours=5, minutes=50)
        )
        db.session.add(agent_log1)
        db.session.add(agent_log2)

        db.session.commit()

        print("\n=======================================================")
        print("ANNADATA AI Seed Data Initialized Successfully!")
        print("=======================================================")
        print(f"Users: {User.query.count()} (Roles: restaurant, ngo, volunteer, admin)")
        print(f"Restaurants: {Restaurant.query.count()}")
        print(f"NGOs: {NGO.query.count()}")
        print(f"Volunteers: {Volunteer.query.count()}")
        print(f"Food Donations: {FoodDonation.query.count()} (Suitable, Flagged, Emergency)")
        print(f"Rescue Missions: {RescueMission.query.count()}")
        print(f"Verified Impact Records: {ImpactRecord.query.count()}")
        print(f"Beneficiary Demands: {BeneficiaryDemand.query.count()}")
        print("\nDemo Login Credentials for Academic Evaluation & Viva:")
        print("  Restaurant: restaurant@example.com / password123")
        print("  NGO:        ngo@example.com / password123")
        print("  Volunteer:  volunteer@example.com / password123")
        print("  Admin:      admin@example.com / admin123")
        print("=======================================================\n")


if __name__ == '__main__':
    create_sample_data()
