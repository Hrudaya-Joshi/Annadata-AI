"""
ANNADATA AI — Comprehensive Multi-User Demo Seed Script
Populates the database with:
- 8 Donors / Commercial Kitchens & Food Hubs
- 6 Verified NGOs / Community Shelters
- 10 Active Volunteer Couriers
- 1 Admin
- ≥20 Connected Food Rescue Donations across 3 categories (Prepared Food, Fresh Produce, Raw Ingredients)
- ≥10 Connected Rescue Missions spanning all workflow lifecycle states (completed, in-transit, assigned, emergency, etc.)
- Verified Impact Records with transparent categorical distinction
- Beneficiary Demands, Notifications, Audit Logs, and Agent Execution Logs

Safe, repeatable execution for viva demonstrations and academic evaluation.
Run with: .\\venv\\Scripts\\python -m seeds.sample_data
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
        # ==========================================
        # 1. 8 RESTAURANTS / DONORS
        # ==========================================
        donors_data = [
            {
                "email": "restaurant@example.com",
                "name": "Chef Vikram Oberoi",
                "phone": "+91 98450 12345",
                "biz": "Golden Spoon Banquet & Bistro",
                "cuisine": "North & South Indian Multi-Cuisine",
                "addr": "123 100-Ft Road, Indiranagar, Bengaluru",
                "lat": 12.9784, "lng": 77.6408
            },
            {
                "email": "bistro@example.com",
                "name": "Chef Ananya Sen",
                "phone": "+91 98450 67890",
                "biz": "Green Leaf Organic Cafe & Bakery",
                "cuisine": "Continental, Breads & Organic Salads",
                "addr": "45 80-Ft Road, Koramangala 4th Block, Bengaluru",
                "lat": 12.9345, "lng": 77.6265
            },
            {
                "email": "harvest@example.com",
                "name": "Ramesh Gowda",
                "phone": "+91 98450 11223",
                "biz": "Sahyadri Fresh Farmers Collective",
                "cuisine": "Fresh Fruits, Vegetables & Greens",
                "addr": "K.R. Market Wholesale Yard, Kalasipalya, Bengaluru",
                "lat": 12.9642, "lng": 77.5768
            },
            {
                "email": "grains@example.com",
                "name": "Harish Patel",
                "phone": "+91 98450 44556",
                "biz": "Annapurna Grain Merchants & Wholesale Pantry",
                "cuisine": "Bulk Rice, Pulses, Wheat & Staples",
                "addr": "APMC Yard Gate 2, Yeshwanthpur, Bengaluru",
                "lat": 13.0234, "lng": 77.5489
            },
            {
                "email": "tajbanquets@example.com",
                "name": "Executive Chef Sanjeev Rao",
                "phone": "+91 98450 77889",
                "biz": "Royal Orchid Convention & Wedding Banquets",
                "cuisine": "Large Scale Banquet Meals & Buffet",
                "addr": "1 Golf Avenue, HAL Old Airport Road, Bengaluru",
                "lat": 12.9592, "lng": 77.6534
            },
            {
                "email": "canteen@example.com",
                "name": "M. Murugan",
                "phone": "+91 98450 99001",
                "biz": "TechPark Central Campus Canteen",
                "cuisine": "South Indian Thalis, Rice & Sambar",
                "addr": "Ecospace Business Park, Bellandur, Bengaluru",
                "lat": 12.9260, "lng": 77.6834
            },
            {
                "email": "orchard@example.com",
                "name": "Kavitha Reddy",
                "phone": "+91 98450 33445",
                "biz": "Nandi Valley Fruit Orchards & Produce Hub",
                "cuisine": "Seasonal Citrus, Melons & Farm Surplus",
                "addr": "Yelahanka New Town Fruit Hub, Bengaluru",
                "lat": 13.1007, "lng": 77.5963
            },
            {
                "email": "heritagebakery@example.com",
                "name": "Farhan Akhtar",
                "phone": "+91 98450 55667",
                "biz": "Heritage Artisanal Bakehouse & Patisserie",
                "cuisine": "Whole Wheat Loaves, Buns & Snacks",
                "addr": "Commercial Street, Tasker Town, Bengaluru",
                "lat": 12.9822, "lng": 77.6083
            }
        ]

        restaurants = []
        rest_users = []
        for d in donors_data:
            u = User(
                role='restaurant',
                email=d['email'],
                full_name=d['name'],
                phone=d['phone'],
                is_active=True
            )
            u.set_password('password123')
            db.session.add(u)
            db.session.flush()
            rest_users.append(u)

            r = Restaurant(
                user_id=u.id,
                business_name=d['biz'],
                food_type=d['cuisine'],
                location_address=d['addr'],
                latitude=d['lat'],
                longitude=d['lng']
            )
            db.session.add(r)
            restaurants.append(r)

        # ==========================================
        # 2. 6 NGOS / SHELTERS
        # ==========================================
        ngos_data = [
            {
                "email": "ngo@example.com",
                "lead": "Sister Mary Verghese",
                "phone": "+91 98451 11223",
                "org": "Helping Hands Community Shelter",
                "reg": "NGO-BLR-2019-4821",
                "addr": "12 1st Cross, Austin Town, Neelasandra, Bengaluru",
                "lat": 12.9611, "lng": 77.6189,
                "cap": 120,
                "cats": "prepared_food,fresh_produce,raw_ingredients",
                "storage": "Hot Holding, Refrigerator, Dry Pantry"
            },
            {
                "email": "ashraya@example.com",
                "lead": "Dr. Pradeep Kumar",
                "phone": "+91 98451 44556",
                "biz_org": "Ashraya Children Home & Night Refuge",
                "reg": "NGO-BLR-2016-1102",
                "addr": "88 Ulsoor Road, Halasuru, Bengaluru",
                "lat": 12.9780, "lng": 77.6250,
                "cap": 85,
                "cats": "prepared_food,fresh_produce",
                "storage": "Commercial Refrigerator, Warm Trays"
            },
            {
                "email": "spandana@example.com",
                "lead": "Lakshmi Narayana",
                "phone": "+91 98451 77889",
                "biz_org": "Spandana Seva Old Age Care Home",
                "reg": "NGO-BLR-2018-3341",
                "addr": "34 5th Main, Malleshwaram, Bengaluru",
                "lat": 13.0031, "lng": 77.5694,
                "cap": 75,
                "cats": "prepared_food,raw_ingredients",
                "storage": "Pantry, Insulated Cool Box"
            },
            {
                "email": "akshaya@example.com",
                "lead": "Mohan Raj",
                "phone": "+91 98451 99001",
                "biz_org": "Akshaya Community Feeding Mission",
                "reg": "NGO-BLR-2020-5512",
                "addr": "56 Sarjapur Road, Kaikondrahalli, Bengaluru",
                "lat": 12.9123, "lng": 77.6745,
                "cap": 250,
                "cats": "prepared_food,fresh_produce,raw_ingredients",
                "storage": "Walk-in Cooler, Deep Pantry, Industrial Kitchen"
            },
            {
                "email": "sneha@example.com",
                "lead": "Fatima Begum",
                "phone": "+91 98451 22334",
                "biz_org": "Sneha Care Transit Home & Youth Shelter",
                "reg": "NGO-BLR-2021-7789",
                "addr": "18 Victoria Road, Shanthala Nagar, Bengaluru",
                "lat": 12.9678, "lng": 77.6112,
                "cap": 90,
                "cats": "prepared_food,fresh_produce",
                "storage": "Refrigeration Unit, Hot Case"
            },
            {
                "email": "karuna@example.com",
                "lead": "Girish Bhat",
                "phone": "+91 98451 66778",
                "biz_org": "Karuna Hunger Relief & Community Kitchen",
                "reg": "NGO-BLR-2017-9034",
                "addr": "72 Chord Road, Rajajinagar, Bengaluru",
                "lat": 12.9915, "lng": 77.5523,
                "cap": 180,
                "cats": "raw_ingredients,fresh_produce,prepared_food",
                "storage": "Bulk Grain Silos, Cold Room, Food Warmers"
            }
        ]

        ngos = []
        ngo_users = []
        for n in ngos_data:
            u = User(
                role='ngo',
                email=n['email'],
                full_name=n['lead'],
                phone=n['phone'],
                is_active=True
            )
            u.set_password('password123')
            db.session.add(u)
            db.session.flush()
            ngo_users.append(u)

            ngo_entry = NGO(
                user_id=u.id,
                organization_name=n.get('org') or n.get('biz_org'),
                registration_number=n['reg'],
                capacity_people=n['cap'],
                location_address=n['addr'],
                latitude=n['lat'],
                longitude=n['lng'],
                accepted_categories=n['cats'],
                storage_facilities=n['storage']
            )
            db.session.add(ngo_entry)
            ngos.append(ngo_entry)

        # ==========================================
        # 3. 10 VOLUNTEER COURIERS
        # ==========================================
        volunteers_data = [
            {"email": "volunteer@example.com", "name": "Rahul Verma", "phone": "+91 98452 33445", "vehicle": "bike", "km": 8.0, "lat": 12.9750, "lng": 77.6350, "avail": True},
            {"email": "deepa@example.com", "name": "Deepa Sundaram", "phone": "+91 98454 77889", "vehicle": "scooter", "km": 10.0, "lat": 12.9380, "lng": 77.6210, "avail": True},
            {"email": "arjun@example.com", "name": "Arjun Nair", "phone": "+91 98455 12121", "vehicle": "car", "km": 15.0, "lat": 12.9550, "lng": 77.6400, "avail": True},
            {"email": "karan@example.com", "name": "Karan Malhotra", "phone": "+91 98455 23232", "vehicle": "bike", "km": 6.0, "lat": 12.9900, "lng": 77.5800, "avail": False},
            {"email": "priya@example.com", "name": "Priya Deshmukh", "phone": "+91 98455 34343", "vehicle": "scooter", "km": 12.0, "lat": 12.9200, "lng": 77.6600, "avail": True},
            {"email": "rohit@example.com", "name": "Rohit Joseph", "phone": "+91 98455 45454", "vehicle": "van", "km": 20.0, "lat": 13.0100, "lng": 77.5600, "avail": True},
            {"email": "sneha.v@example.com", "name": "Sneha Kulkarni", "phone": "+91 98455 56565", "vehicle": "bike", "km": 7.0, "lat": 12.9700, "lng": 77.6100, "avail": True},
            {"email": "vikas@example.com", "name": "Vikas Hegde", "phone": "+91 98455 67676", "vehicle": "car", "km": 14.0, "lat": 12.9400, "lng": 77.5900, "avail": True},
            {"email": "meera@example.com", "name": "Meera Iyer", "phone": "+91 98455 78787", "vehicle": "scooter", "km": 9.0, "lat": 13.0300, "lng": 77.5500, "avail": True},
            {"email": "tanveer@example.com", "name": "Tanveer Ahmed", "phone": "+91 98455 89898", "vehicle": "bike", "km": 8.0, "lat": 12.9600, "lng": 77.6700, "avail": True}
        ]

        volunteers = []
        vol_users = []
        for v in volunteers_data:
            u = User(
                role='volunteer',
                email=v['email'],
                full_name=v['name'],
                phone=v['phone'],
                is_active=True
            )
            u.set_password('password123')
            db.session.add(u)
            db.session.flush()
            vol_users.append(u)

            vol = Volunteer(
                user_id=u.id,
                available=v['avail'],
                max_distance_km=v['km'],
                vehicle_type=v['vehicle'],
                latitude=v['lat'],
                longitude=v['lng']
            )
            db.session.add(vol)
            volunteers.append(vol)

        # ==========================================
        # 4. SYSTEM ADMIN
        # ==========================================
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

        print("2. Creating 22 diverse, connected food donations across all 3 categories...")
        # ==========================================
        # 5. 22 CONNECTED DONATIONS (Categorical breakdown)
        # ==========================================
        donations_specs = [
            # 1 to 10: Prepared Food
            {
                "rest": restaurants[0],
                "cat": "prepared_food", "subcat": "cooked meals",
                "name": "Vegetable Dum Biryani & Mirchi Ka Salan",
                "qty": 40, "unit": "packets", "kg": 20.0, "meals": 40,
                "hours_ago": 7, "valid_hours": 3, "dead_hours": 2,
                "temp": "Hot Holding (68°C)", "pack": "Thermal foil trays",
                "status": "delivered", "score": 96.0,
                "desc": "Freshly packed aromatic vegetable biryani in sealed meal containers."
            },
            {
                "rest": restaurants[1],
                "cat": "prepared_food", "subcat": "baked goods",
                "name": "Artisanal Multigrain Sourdough Loaves",
                "qty": 25, "unit": "pieces", "kg": 15.0, "meals": 30,
                "hours_ago": 5, "valid_hours": 20, "dead_hours": 3,
                "temp": "Room Temperature", "pack": "Sanitized craft paper sleeves",
                "status": "delivered", "score": 98.0,
                "desc": "Crusty multigrain sourdough breads baked this morning."
            },
            {
                "rest": restaurants[4],
                "cat": "prepared_food", "subcat": "cooked meals",
                "name": "Paneer Butter Masala & Tawa Rotis",
                "qty": 60, "unit": "packets", "kg": 30.0, "meals": 60,
                "hours_ago": 3, "valid_hours": 1, "dead_hours": 0.5,
                "temp": "Hot Holding (64°C)", "pack": "Insulated food trays",
                "status": "delivered", "score": 94.0,
                "desc": "Rich paneer curry and soft rotis from lunchtime banquet service."
            },
            {
                "rest": restaurants[5],
                "cat": "prepared_food", "subcat": "cooked meals",
                "name": "South Indian Sambar, Rasam & Steamed Rice",
                "qty": 50, "unit": "servings", "kg": 25.0, "meals": 50,
                "hours_ago": 4, "valid_hours": 4, "dead_hours": 1.5,
                "temp": "Hot Holding (70°C)", "pack": "Stainless insulated urns",
                "status": "delivered", "score": 97.0,
                "desc": "Nutritious lentil sambar, tomato rasam and hot steamed rice from lunch buffet."
            },
            {
                "rest": restaurants[7],
                "cat": "prepared_food", "subcat": "baked goods",
                "name": "Assorted Vegetable Puffs & Wheat Buns",
                "qty": 35, "unit": "pieces", "kg": 10.5, "meals": 35,
                "hours_ago": 2, "valid_hours": 12, "dead_hours": 4,
                "temp": "Room Temperature", "pack": "Bakery display boxes",
                "status": "delivered", "score": 95.0,
                "desc": "Oven fresh potato-pea puffs and whole wheat rolls."
            },
            {
                "rest": restaurants[0],
                "cat": "prepared_food", "subcat": "cooked meals",
                "name": "Dal Makhani & Jeera Pulao Batch",
                "qty": 45, "unit": "packets", "kg": 22.5, "meals": 45,
                "hours_ago": 2, "valid_hours": 3, "dead_hours": 1,
                "temp": "Hot Holding (65°C)", "pack": "Food-grade sealed containers",
                "status": "in_transit", "score": 96.0,
                "desc": "Slow-cooked black lentils in butter gravy with spiced cumin rice."
            },
            {
                "rest": restaurants[4],
                "cat": "prepared_food", "subcat": "cooked meals",
                "name": "Mixed Vegetable Korma & Poori Boxes",
                "qty": 50, "unit": "packets", "kg": 25.0, "meals": 50,
                "hours_ago": 1, "valid_hours": 2, "dead_hours": 0.8,
                "temp": "Hot Holding (62°C)", "pack": "Foil meal packs",
                "status": "matched", "score": 93.0,
                "desc": "Coconut vegetable curry and puffed whole wheat pooris."
            },
            {
                "rest": restaurants[1],
                "cat": "prepared_food", "subcat": "cooked meals",
                "name": "Penne Arbiatta & Garlic Herb Bread",
                "qty": 20, "unit": "servings", "kg": 10.0, "meals": 20,
                "hours_ago": 1, "valid_hours": 2, "dead_hours": 1.0,
                "temp": "Hot Holding (60°C)", "pack": "Biodegradable meal boxes",
                "status": "submitted", "score": 92.0,
                "desc": "Pasta in rich tomato basil sauce with toasted garlic baguettes."
            },
            {
                "rest": restaurants[5],
                "cat": "prepared_food", "subcat": "cooked meals",
                "name": "Curd Rice with Pomegranate & Pickle",
                "qty": 30, "unit": "packets", "kg": 15.0, "meals": 30,
                "hours_ago": 2, "valid_hours": 4, "dead_hours": 2.0,
                "temp": "Chilled (6°C)", "pack": "Sealed plastic containers",
                "status": "assigned", "score": 97.0,
                "desc": "Cool, comforting tempered yoghurt rice garnished with pomegranate seeds."
            },
            {
                "rest": restaurants[0],
                "cat": "prepared_food", "subcat": "cooked meals",
                "name": "Hyderabadi Veg Biryani (Late Night Emergency)",
                "qty": 35, "unit": "packets", "kg": 17.5, "meals": 35,
                "hours_ago": 1, "valid_hours": 1.2, "dead_hours": 0.5,
                "temp": "Hot Holding (66°C)", "pack": "Foil meal trays",
                "status": "emergency", "score": 91.0,
                "desc": "Emergency rescue batch with only 30 minutes left before deadline."
            },

            # 11 to 16: Fresh Produce
            {
                "rest": restaurants[2],
                "cat": "fresh_produce", "subcat": "vegetables",
                "name": "Farm Crisp Tomatoes, Carrots & Capsicum Crates",
                "qty": 80, "unit": "kg", "kg": 80.0, "meals": 0,
                "hours_ago": 12, "valid_hours": 48, "dead_hours": 24,
                "temp": "Cool & Ventilated", "pack": "Plastic ventilated crates",
                "status": "delivered", "score": 99.0,
                "desc": "Freshly sorted Grade-A farm produce surplus from morning mandi auction."
            },
            {
                "rest": restaurants[2],
                "cat": "fresh_produce", "subcat": "leafy greens",
                "name": "Organic Spinach & Fenugreek Bundles",
                "qty": 30, "unit": "kg", "kg": 30.0, "meals": 0,
                "hours_ago": 8, "valid_hours": 24, "dead_hours": 12,
                "temp": "Ambient Shaded", "pack": "Open wicker baskets",
                "status": "delivered", "score": 98.0,
                "desc": "Crisp green leafy vegetables rich in iron and nutrients."
            },
            {
                "rest": restaurants[6],
                "cat": "fresh_produce", "subcat": "fruits",
                "name": "Sweet Nandi Bananas & Citrus Oranges",
                "qty": 65, "unit": "kg", "kg": 65.0, "meals": 0,
                "hours_ago": 6, "valid_hours": 72, "dead_hours": 36,
                "temp": "Room Temperature", "pack": "Corrugated ventilated boxes",
                "status": "delivered", "score": 100.0,
                "desc": "Ripe yellow bananas and juicy oranges suitable for immediate consumption."
            },
            {
                "rest": restaurants[2],
                "cat": "fresh_produce", "subcat": "vegetables",
                "name": "Green Beans, Cauliflower & Potatoes",
                "qty": 55, "unit": "kg", "kg": 55.0, "meals": 0,
                "hours_ago": 3, "valid_hours": 48, "dead_hours": 24,
                "temp": "Cool & Ventilated", "pack": "Mesh ventilated sacks",
                "status": "in_transit", "score": 97.0,
                "desc": "Assorted cooking vegetables ideal for community shelter kitchens."
            },
            {
                "rest": restaurants[6],
                "cat": "fresh_produce", "subcat": "fruits",
                "name": "Papaya, Watermelon & Guava Harvest",
                "qty": 70, "unit": "kg", "kg": 70.0, "meals": 0,
                "hours_ago": 2, "valid_hours": 60, "dead_hours": 30,
                "temp": "Cool Shade", "pack": "Fruit crates",
                "status": "matched", "score": 96.0,
                "desc": "Freshly picked vitamin-rich fruits for children and senior homes."
            },
            {
                "rest": restaurants[2],
                "cat": "fresh_produce", "subcat": "vegetables",
                "name": "Farm Fresh Cabbage & Beetroots",
                "qty": 40, "unit": "kg", "kg": 40.0, "meals": 0,
                "hours_ago": 1, "valid_hours": 72, "dead_hours": 36,
                "temp": "Ambient Room Temp", "pack": "Jute mesh crates",
                "status": "submitted", "score": 95.0,
                "desc": "Sturdy root vegetables and crunchy cabbages with long keeping quality."
            },

            # 17 to 22: Raw Ingredients
            {
                "rest": restaurants[3],
                "cat": "raw_ingredients", "subcat": "rice & grains",
                "name": "Sona Masoori Rice (25 kg Sacks)",
                "qty": 100, "unit": "kg", "kg": 100.0, "meals": 0,
                "hours_ago": 24, "valid_hours": 720, "dead_hours": 120,
                "temp": "Dry Storage", "pack": "Factory sealed 25 kg poly-woven sacks",
                "status": "delivered", "score": 100.0,
                "desc": "4 sacks of 25 kg premium polished Sona Masoori cooking rice."
            },
            {
                "rest": restaurants[3],
                "cat": "raw_ingredients", "subcat": "pulses & lentils",
                "name": "Unpolished Toor Dal & Moong Dal",
                "qty": 50, "unit": "kg", "kg": 50.0, "meals": 0,
                "hours_ago": 18, "valid_hours": 720, "dead_hours": 120,
                "temp": "Dry Storage", "pack": "Multi-layer moisture proof bags",
                "status": "delivered", "score": 100.0,
                "desc": "High-protein unpolished lentils in original commercial packaging."
            },
            {
                "rest": restaurants[3],
                "cat": "raw_ingredients", "subcat": "wheat & flour",
                "name": "Chakki Whole Wheat Atta",
                "qty": 75, "unit": "kg", "kg": 75.0, "meals": 0,
                "hours_ago": 10, "valid_hours": 360, "dead_hours": 96,
                "temp": "Dry Storage", "pack": "Laminated moisture-proof paper bags",
                "status": "delivered", "score": 100.0,
                "desc": "Freshly milled 100% whole wheat stone-ground flour."
            },
            {
                "rest": restaurants[3],
                "cat": "raw_ingredients", "subcat": "cooking staples",
                "name": "Refined Sunflower Oil Cans (15L)",
                "qty": 30, "unit": "kg", "kg": 30.0, "meals": 0,
                "hours_ago": 5, "valid_hours": 720, "dead_hours": 140,
                "temp": "Room Temperature", "pack": "Sealed metal tins",
                "status": "in_transit", "score": 99.0,
                "desc": "Two 15-liter sealed food-grade cooking oil tins with ISI certification."
            },
            {
                "rest": restaurants[3],
                "cat": "raw_ingredients", "subcat": "rice & grains",
                "name": "Kolam Rice & Rava / Semolina",
                "qty": 60, "unit": "kg", "kg": 60.0, "meals": 0,
                "hours_ago": 2, "valid_hours": 720, "dead_hours": 100,
                "temp": "Dry Pantry", "pack": "Factory sealed bags",
                "status": "assigned", "score": 98.0,
                "desc": "Staple grains for community kitchen breakfast and meal preparations."
            },
            {
                "rest": restaurants[3],
                "cat": "raw_ingredients", "subcat": "pulses & lentils",
                "name": "Chana Dal & Green Gram / Moong",
                "qty": 40, "unit": "kg", "kg": 40.0, "meals": 0,
                "hours_ago": 1, "valid_hours": 720, "dead_hours": 120,
                "temp": "Dry Pantry", "pack": "Moisture-sealed polybags",
                "status": "submitted", "score": 99.0,
                "desc": "Wholesale pulses surplus with over 6 months remaining shelf life."
            }
        ]

        food_donations = []
        for i, s in enumerate(donations_specs, start=1):
            created_dt = now - timedelta(hours=s['hours_ago'])
            exp_dt = created_dt + timedelta(hours=s['valid_hours'])
            dead_dt = created_dt + timedelta(hours=s['dead_hours'])

            don_stat = 'delivered' if s['status'] == 'delivered' else (
                'in_transit' if s['status'] == 'in_transit' else (
                    'matched' if s['status'] in ['matched', 'assigned'] else 'available'
                )
            )

            code = f"ANN-RESCUE-202611-{1000 + i}"
            don = FoodDonation(
                rescue_code=code,
                restaurant_id=s['rest'].id,
                donation_category=s['cat'],
                food_name=s['name'],
                category=s['subcat'],
                quantity=s['qty'],
                unit=s['unit'],
                preparation_time=created_dt - timedelta(hours=1),
                expiry_time=exp_dt,
                collection_deadline=dead_dt,
                description=s['desc'],
                location_address=s['rest'].location_address,
                latitude=s['rest'].latitude,
                longitude=s['rest'].longitude,
                status=don_stat,
                suitability_score=s['score'],
                analysis_report=f'{{"suitable": true, "issues": [], "risk_level": "low", "category": "{s["cat"]}"}}',
                storage_temperature=s['temp'],
                dietary_flags="Vegetarian",
                packaging_type=s['pack'],
                produce_type=s['name'] if s['cat'] == 'fresh_produce' else None,
                freshness_condition="Freshly Harvested" if s['cat'] == 'fresh_produce' else None,
                harvest_date=created_dt - timedelta(days=1) if s['cat'] == 'fresh_produce' else None,
                ingredient_name=s['name'] if s['cat'] == 'raw_ingredients' else None,
                packaging_condition="Factory Sealed" if s['cat'] == 'raw_ingredients' else None,
                storage_requirements="Cool Dry Pantry" if s['cat'] == 'raw_ingredients' else None,
                created_at=created_dt
            )
            db.session.add(don)
            db.session.flush()

            # Safety Assessment
            safe = FoodSafetyAssessment(
                donation_id=don.id,
                visual_inspection_passed=True,
                packaging_intact=True,
                temperature_controlled=(s['cat'] == 'prepared_food'),
                allergens_declared=True,
                hygiene_verified=True,
                temperature_celsius=65.0 if s['cat'] == 'prepared_food' else 22.0,
                risk_level='low',
                ai_risk_observations=f"Safety inspection passed for {s['cat'].replace('_', ' ')}.",
                verified_by_user_id=s['rest'].user_id,
                verified_at=created_dt
            )
            db.session.add(safe)
            food_donations.append(don)

        # ==========================================
        # 6. 12 RESCUE MISSIONS (Covering various lifecycle states)
        # ==========================================
        print("3. Creating 12 connected rescue missions across all workflow stages...")
        missions_specs = [
            # 1 to 7: Completed & Verified Missions (Delivered Safe)
            {"don_idx": 0, "ngo": ngos[0], "vol": volunteers[0], "status": "delivery_confirmed", "mins_ago": 280, "dist": 4.2},
            {"don_idx": 1, "ngo": ngos[1], "vol": volunteers[1], "status": "delivery_confirmed", "mins_ago": 220, "dist": 3.8},
            {"don_idx": 2, "ngo": ngos[0], "vol": volunteers[2], "status": "delivery_confirmed", "mins_ago": 160, "dist": 5.1},
            {"don_idx": 3, "ngo": ngos[3], "vol": volunteers[4], "status": "delivery_confirmed", "mins_ago": 140, "dist": 6.5},
            {"don_idx": 4, "ngo": ngos[4], "vol": volunteers[6], "status": "delivery_confirmed", "mins_ago": 90,  "dist": 2.9},
            {"don_idx": 10, "ngo": ngos[3], "vol": volunteers[5], "status": "delivery_confirmed", "mins_ago": 360, "dist": 7.4}, # Fresh produce
            {"don_idx": 11, "ngo": ngos[0], "vol": volunteers[7], "status": "delivery_confirmed", "mins_ago": 300, "dist": 4.5}, # Fresh greens
            {"don_idx": 12, "ngo": ngos[1], "vol": volunteers[0], "status": "delivery_confirmed", "mins_ago": 200, "dist": 5.0}, # Fruit
            {"don_idx": 16, "ngo": ngos[5], "vol": volunteers[5], "status": "delivery_confirmed", "mins_ago": 480, "dist": 6.8}, # Raw rice
            {"don_idx": 17, "ngo": ngos[3], "vol": volunteers[2], "status": "delivery_confirmed", "mins_ago": 400, "dist": 8.1}, # Raw pulses
            {"don_idx": 18, "ngo": ngos[5], "vol": volunteers[7], "status": "delivery_confirmed", "mins_ago": 260, "dist": 5.7}, # Raw wheat

            # 12 to 14: Active In-Transit Missions
            {"don_idx": 5, "ngo": ngos[0], "vol": volunteers[0], "status": "food_collected", "mins_ago": 30, "dist": 3.5},
            {"don_idx": 13, "ngo": ngos[3], "vol": volunteers[4], "status": "delivery_initiated", "mins_ago": 20, "dist": 5.2},
            {"don_idx": 19, "ngo": ngos[5], "vol": volunteers[5], "status": "pickup_initiated", "mins_ago": 15, "dist": 7.0},

            # 15 to 16: Matched & Assigned Missions
            {"don_idx": 6, "ngo": ngos[1], "vol": volunteers[1], "status": "volunteer_assigned", "mins_ago": 40, "dist": 4.1},
            {"don_idx": 14, "ngo": ngos[4], "vol": volunteers[2], "status": "ngo_accepted", "mins_ago": 50, "dist": 3.2}
        ]

        created_missions = []
        for j, ms in enumerate(missions_specs, start=1):
            don = food_donations[ms['don_idx']]
            spec = donations_specs[ms['don_idx']]
            m_code = f"ANN-MSN-202611-{j:03d}"

            # Create DonationRequest linking donation to NGO
            req_stat = 'accepted' if ms['status'] != 'ngo_matching' else 'pending'
            d_req = DonationRequest(
                donation_id=don.id,
                ngo_id=ms['ngo'].id,
                status=req_stat,
                match_score=95.5,
                distance_km=ms['dist'],
                response_notes=f"Auto-matched by Smart Allocation Service for {ms['ngo'].organization_name}.",
                requested_at=don.created_at + timedelta(minutes=10),
                responded_at=don.created_at + timedelta(minutes=15)
            )
            db.session.add(d_req)
            db.session.flush()

            # Create Mission
            pickup_dt = don.created_at + timedelta(minutes=30) if ms['status'] in ['food_collected', 'delivery_initiated', 'delivery_confirmed'] else None
            deliv_dt = don.created_at + timedelta(minutes=65) if ms['status'] == 'delivery_confirmed' else None

            mis = RescueMission(
                mission_code=m_code,
                donation_id=don.id,
                ngo_id=ms['ngo'].id,
                volunteer_id=ms['vol'].id if ms['vol'] else None,
                status=ms['status'],
                pickup_deadline=don.collection_deadline,
                delivery_deadline=don.expiry_time,
                verification_pin=f"{(2000 + j * 13) % 9000 + 1000}",
                pickup_time=pickup_dt,
                delivery_time=deliv_dt,
                delivery_notes=f"Delivered safely to {ms['ngo'].organization_name}." if deliv_dt else None,
                created_at=don.created_at + timedelta(minutes=15)
            )
            db.session.add(mis)
            db.session.flush()
            created_missions.append(mis)

            # If completed, create verified ImpactRecord
            if ms['status'] == 'delivery_confirmed':
                kg_amt = spec['kg']
                meals_cnt = spec['meals']
                bene_cnt = int(spec['meals'] * 1.0) if meals_cnt > 0 else int(kg_amt * 2.5)

                imp = ImpactRecord(
                    mission_id=mis.id,
                    donation_id=don.id,
                    donation_category=spec['cat'],
                    quantity_kg=kg_amt,
                    meals_served=meals_cnt,
                    beneficiaries_reached=bene_cnt,
                    co2_saved_kg=round(kg_amt * 2.5, 1),
                    water_saved_liters=round(kg_amt * 250.0, 1),
                    verified_at=deliv_dt
                )
                db.session.add(imp)

        # ==========================================
        # 7. BENEFICIARY DEMANDS, NOTIFICATIONS & LOGS
        # ==========================================
        print("4. Creating realistic beneficiary demands, notifications, and AI logs...")
        demands_data = [
            {"ngo": ngos[0], "cat": "prepared_food", "sub": "cooked meals", "qty": 80, "unit": "meals", "urg": "critical", "notes": "Evening dinner service for 80 unhoused individuals at Austin Town shelter."},
            {"ngo": ngos[1], "cat": "fresh_produce", "sub": "fruits", "qty": 40, "unit": "kg", "urg": "elevated", "notes": "Nutritious seasonal fruit requirement for 85 growing children."},
            {"ngo": ngos[3], "cat": "raw_ingredients", "sub": "rice & grains", "qty": 200, "unit": "kg", "urg": "routine", "notes": "Weekly grain replenishment for community kitchen supplying 250 thalis daily."},
            {"ngo": ngos[5], "cat": "raw_ingredients", "sub": "pulses & lentils", "qty": 50, "unit": "kg", "urg": "routine", "notes": "Toor dal and moong dal for nutrition-dense elder soups."},
            {"ngo": ngos[2], "cat": "prepared_food", "sub": "cooked meals", "qty": 50, "unit": "meals", "urg": "routine", "notes": "Soft-diet meals appropriate for senior citizens."}
        ]

        for d in demands_data:
            bd = BeneficiaryDemand(
                ngo_id=d['ngo'].id,
                donation_category=d['cat'],
                category=d['sub'],
                required_quantity=d['qty'],
                unit=d['unit'],
                urgency_level=d['urg'],
                notes=d['notes'],
                target_date=now + timedelta(hours=8)
            )
            db.session.add(bd)

        # Notifications
        notif1 = Notification(
            user_id=ngo_users[0].id,
            title='URGENT: Emergency Food Rescue Alert',
            message='Donation #10 (Hyderabadi Veg Biryani) collection deadline is within 30 minutes in Indiranagar sector.',
            category='urgent',
            link_url='/ngo/dashboard',
            is_read=False,
            created_at=now - timedelta(minutes=20)
        )
        notif2 = Notification(
            user_id=rest_users[0].id,
            title='Rescue Mission Completed!',
            message='Mission ANN-MSN-202611-001 has been safely delivered to Helping Hands Community Shelter with verified PIN.',
            category='success',
            link_url='/restaurant/dashboard',
            is_read=True,
            created_at=now - timedelta(hours=3)
        )
        notif3 = Notification(
            user_id=vol_users[0].id,
            title='New Mission Assigned',
            message='You have been assigned mission ANN-MSN-202611-012 for hot meal pickup at Golden Spoon Banquet.',
            category='info',
            link_url='/volunteer/dashboard',
            is_read=False,
            created_at=now - timedelta(minutes=25)
        )
        db.session.add(notif1)
        db.session.add(notif2)
        db.session.add(notif3)

        # Audit Logs
        audit1 = AuditLog(
            user_id=admin_user.id,
            action='SYSTEM_INITIALIZATION',
            target_type='Database',
            details='ANNADATA AI multi-category production demonstration network seeded successfully.',
            created_at=now - timedelta(days=1)
        )
        audit2 = AuditLog(
            user_id=ngo_users[0].id,
            action='DELIVERY_CONFIRMATION_PIN',
            target_type='RescueMission',
            details='Sister Mary Verghese entered 4-digit PIN to confirm receipt of 40 hot meals.',
            created_at=now - timedelta(hours=4)
        )
        db.session.add(audit1)
        db.session.add(audit2)

        # Agent Logs
        for k in range(5):
            don_item = food_donations[k]
            al1 = AgentExecutionLog(
                donation_id=don_item.id,
                agent_name='FoodAnalysisAgent',
                task='safety_analysis',
                input_data=f'{{"donation_id": {don_item.id}, "food_name": "{don_item.food_name}", "category": "{don_item.donation_category}"}}',
                output_data=f'{{"suitable": true, "issues": [], "suitability_score": {don_item.suitability_score}, "category": "{don_item.donation_category}"}}',
                status='success',
                created_at=don_item.created_at + timedelta(minutes=2)
            )
            al2 = AgentExecutionLog(
                donation_id=don_item.id,
                agent_name='NGOMatchingAgent',
                task='smart_allocation',
                input_data=f'{{"donation_id": {don_item.id}, "category": "{don_item.donation_category}"}}',
                output_data='{"top_match": "Helping Hands Community Shelter", "score": 96.5, "fairness_index": 1.0}',
                status='success',
                created_at=don_item.created_at + timedelta(minutes=5)
            )
            db.session.add(al1)
            db.session.add(al2)

        db.session.commit()

        print("\n=======================================================")
        print("ANNADATA AI Demo Seed Data Populated Successfully!")
        print("=======================================================")
        print(f"Users: {User.query.count()} (Roles: restaurant, ngo, volunteer, admin)")
        print(f"Restaurants / Donors: {Restaurant.query.count()} (Target: >=8)")
        print(f"NGOs / Shelters:      {NGO.query.count()} (Target: >=6)")
        print(f"Volunteers:           {Volunteer.query.count()} (Target: >=10)")
        print(f"Food Donations:       {FoodDonation.query.count()} (Target: >=20)")
        print(f"Rescue Missions:      {RescueMission.query.count()} (Target: >=10)")
        print(f"Verified Impact:      {ImpactRecord.query.count()}")
        print(f"Beneficiary Demands:  {BeneficiaryDemand.query.count()}")
        print("\nDemo Login Credentials for Academic Evaluation & Viva:")
        print("  Restaurant / Donor:  restaurant@example.com   / password123")
        print("  NGO / Shelter:       ngo@example.com          / password123")
        print("  Volunteer Courier:   volunteer@example.com    / password123")
        print("  System Admin:        admin@example.com        / admin123")
        print("=======================================================\n")


if __name__ == '__main__':
    create_sample_data()
