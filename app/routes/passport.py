from flask import Blueprint, render_template, abort, Response
from flask_login import current_user
from app.models import FoodDonation, RescueMission, PickupAssignment
from app.services.qr_service import QRService

passport_bp = Blueprint('passport', __name__, url_prefix='/passport')


@passport_bp.route('/<rescue_code>')
def view_passport(rescue_code):
    donation = FoodDonation.query.filter_by(rescue_code=rescue_code).first()
    if not donation:
        # Check by integer ID fallback
        if rescue_code.isdigit():
            donation = FoodDonation.query.get(int(rescue_code))
        if not donation:
            abort(404)

    # Associated mission
    mission = RescueMission.query.filter_by(donation_id=donation.id).first()

    # Public-safety data masking
    is_authorized = (
        current_user.is_authenticated and (
            current_user.role == 'admin' or
            (current_user.restaurant and current_user.restaurant.id == donation.restaurant_id) or
            (mission and current_user.ngo and current_user.ngo.id == mission.ngo_id) or
            (mission and current_user.volunteer and current_user.volunteer.id == mission.volunteer_id)
        )
    )

    # Anonymized donor representation for public view
    if donation.restaurant:
        raw_name = donation.restaurant.business_name
        if not is_authorized:
            words = raw_name.split()
            masked_name = " ".join([w[0] + "***" if len(w) > 1 else w for w in words])
            public_address = donation.location_address.split(",")[-1].strip() or "Bengaluru Metropolitan Sector"
        else:
            masked_name = raw_name
            public_address = donation.location_address
    else:
        masked_name = "Verified Food Donor"
        public_address = "Metropolitan Area"

    # QR Code Data URI pointing to this passport verification URL
    passport_url = f"/passport/{donation.rescue_code or donation.id}"
    qr_data_uri = QRService.generate_data_uri(passport_url, size=220)

    return render_template(
        'passport/view.html',
        donation=donation,
        mission=mission,
        is_authorized=is_authorized,
        masked_name=masked_name,
        public_address=public_address,
        qr_data_uri=qr_data_uri,
        safety=donation.safety_assessment
    )


@passport_bp.route('/<rescue_code>/qr.svg')
def get_qr_svg(rescue_code):
    donation = FoodDonation.query.filter_by(rescue_code=rescue_code).first()
    if not donation and rescue_code.isdigit():
        donation = FoodDonation.query.get(int(rescue_code))
    if not donation:
        abort(404)

    passport_url = f"/passport/{donation.rescue_code or donation.id}"
    svg = QRService.generate_svg(passport_url, size=300)
    return Response(svg, mimetype='image/svg+xml')
