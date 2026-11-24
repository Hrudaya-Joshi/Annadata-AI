from app.extensions import db
from app.models import NGO, Volunteer, FoodDonation, DonationRequest

def get_all_ngos():
    return NGO.query.filter_by(is_active=True).all()

def get_available_volunteers():
    return Volunteer.query.filter_by(available=True).all()

def get_donation(donation_id):
    return FoodDonation.query.get(donation_id)

def create_request(donation_id, ngo_id, distance_km):
    req = DonationRequest(donation_id=donation_id, ngo_id=ngo_id, distance_km=distance_km, status="pending")
    db.session.add(req)
    db.session.flush()
    return req

def update_donation_status(donation_id, status):
    donation = FoodDonation.query.get(donation_id)
    if donation:
        donation.status = status
        db.session.commit()
    return donation