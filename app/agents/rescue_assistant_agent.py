from app.agents.base_agent import BaseAgent
from app.services.assistant_service import AssistantService


class RescueAssistantAgent(BaseAgent):
    name = "RescueAssistantAgent"

    def run(self, user, message):
        input_data = {"user_id": user.id if user and user.is_authenticated else None, "message": message}
        try:
            result = AssistantService.chat(user, message)
            self.log(None, "assistant_chat", input_data, result, "success")
            return result
        except Exception as e:
            self.log(None, "assistant_chat", input_data, None, "failed", str(e))
            return {"error": str(e), "answer": "I encountered an issue processing your request. Please try again."}
