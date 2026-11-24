from app.agents.base_agent import BaseAgent
from app.services.forecast_service import SurplusForecastingService


class SurplusPredictionAgent(BaseAgent):
    name = "SurplusPredictionAgent"

    def run(self, restaurant_id=None, area_name=None):
        input_data = {"restaurant_id": restaurant_id, "area_name": area_name}
        try:
            overview = SurplusForecastingService.get_intelligence_overview()
            self.log(None, "surplus_prediction", input_data, overview, "success")
            return overview
        except Exception as e:
            self.log(None, "surplus_prediction", input_data, None, "failed", str(e))
            return {"error": str(e)}
