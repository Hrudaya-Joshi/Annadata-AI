from app import create_app, db

app = create_app()

with app.app_context():
    print('Checking database tables...')
    from app.models import User, FoodDonation, RescueMission, ImpactRecord
    print(f'Users in DB: {User.query.count()}')
    print(f'Donations in DB: {FoodDonation.query.count()}')
    print(f'Missions in DB: {RescueMission.query.count()}')
    print(f'Impact records: {ImpactRecord.query.count()}')

    with app.test_client() as client:
        routes_to_test = [
            '/',
            '/login',
            '/register',
            '/intelligence',
            '/impact',
            '/map',
            '/api/intelligence/forecast',
            '/api/impact/stats',
            '/api/map/data',
            '/api/emergencies',
            '/passport/ANN-RESCUE-202611-1001',
            '/passport/ANN-RESCUE-202611-1001/qr.svg',
        ]

        all_ok = True
        for r in routes_to_test:
            res = client.get(r)
            print(f'GET {r} -> {res.status_code}')
            if res.status_code != 200:
                all_ok = False

        # Test login session for authenticated routes
        print('\nTesting authenticated routes...')
        client.post('/login', data={'email': 'restaurant@example.com', 'password': 'password123'})
        for r in ['/restaurant/dashboard', '/restaurant/donations', '/restaurant/donate', '/missions', '/notifications', '/profile']:
            res = client.get(r)
            print(f'Authenticated GET {r} -> {res.status_code}')
            if res.status_code != 200:
                all_ok = False

        client.get('/logout')
        client.post('/login', data={'email': 'ngo@example.com', 'password': 'password123'})
        for r in ['/ngo/dashboard', '/ngo/donations']:
            res = client.get(r)
            print(f'NGO GET {r} -> {res.status_code}')
            if res.status_code != 200:
                all_ok = False

        client.get('/logout')
        client.post('/login', data={'email': 'volunteer@example.com', 'password': 'password123'})
        for r in ['/volunteer/dashboard', '/volunteer/pickups']:
            res = client.get(r)
            print(f'Volunteer GET {r} -> {res.status_code}')
            if res.status_code != 200:
                all_ok = False

        client.get('/logout')
        client.post('/login', data={'email': 'admin@example.com', 'password': 'admin123'})
        for r in ['/admin/dashboard', '/admin/users', '/admin/donations', '/admin/agent-logs', '/admin/audit-logs']:
            res = client.get(r)
            print(f'Admin GET {r} -> {res.status_code}')
            if res.status_code != 200:
                all_ok = False

        if all_ok:
            print('\n>>> ALL 26 ROUTES RETURNED HTTP 200 OK! <<<')
        else:
            print('\nSome routes failed.')
