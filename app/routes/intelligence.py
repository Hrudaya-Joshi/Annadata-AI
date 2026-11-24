from flask import Blueprint, render_template, jsonify
from app.services.forecast_service import SurplusForecastingService
from app.services.emergency_service import EmergencyRescueService

intelligence_bp = Blueprint('intelligence', __name__)


@intelligence_bp.route('/intelligence')
def intelligence_center():
    forecast_report = SurplusForecastingService.get_intelligence_overview()
    emergency_alerts = EmergencyRescueService.scan_and_escalate(threshold_hours=2.0)
    return render_template(
        'intelligence/index.html',
        forecast=forecast_report,
        emergencies=emergency_alerts
    )


@intelligence_bp.route('/api/intelligence/forecast')
def api_forecast():
    return jsonify(SurplusForecastingService.get_intelligence_overview())
