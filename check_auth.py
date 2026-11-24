from app import create_app

app = create_app()

with app.app_context():
    from app import db
    from app.models import User
    db.create_all()
    u = User.query.filter_by(email='test@restaurant.com').first()
    if u:
        db.session.delete(u)
        db.session.commit()

with app.test_client() as client:
    resp = client.post('/register', data={
        'role': 'restaurant',
        'email': 'test@restaurant.com',
        'password': 'password123',
        'confirm_password': 'password123',
        'full_name': 'Test Restaurant',
        'phone': '1234567890',
        'business_name': 'Test Bistro',
        'food_type': 'Italian',
        'location_address': 'Test Address',
        'latitude': 12.97,
        'longitude': 77.59
    }, follow_redirects=True)
    print('Register status:', resp.status_code)

    resp2 = client.post('/login', data={
        'email': 'test@restaurant.com',
        'password': 'password123'
    }, follow_redirects=True)
    print('Login status:', resp2.status_code)

print('Auth flow check complete.')