from app.agents.base_agent import BaseAgent
from app.services.impact_service import ImpactAnalyticsService


class ImpactAnalyticsAgent(BaseAgent):
    name = "ImpactAnalyticsAgent"

    def run(self):
        try:
            impact_data = ImpactAnalyticsService.get_comprehensive_impact()
            self.log(None, "impact_analytics", {}, impact_data, "success")
            return impact_data
        except Exception as e:
            self.log(None, "impact_analytics", {}, None, "failed", str(e))
            return {"error": str(e)}
