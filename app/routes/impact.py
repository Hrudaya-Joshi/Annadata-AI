from flask import Blueprint, render_template, jsonify
from app.services.impact_service import ImpactAnalyticsService

impact_bp = Blueprint('impact', __name__)


@impact_bp.route('/impact')
def impact_dashboard():
    impact_data = ImpactAnalyticsService.get_comprehensive_impact()
    return render_template('impact/index.html', impact=impact_data)


@impact_bp.route('/api/impact/stats')
def api_impact_stats():
    return jsonify(ImpactAnalyticsService.get_comprehensive_impact())
