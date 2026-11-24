import json
from app.extensions import db
from app.models import AgentExecutionLog

class BaseAgent:
    name = "base_agent"

    def log(self, donation_id, task, input_data, output_data, status="success", error=None):
        entry = AgentExecutionLog(
            donation_id=donation_id,
            agent_name=self.name,
            task=task,
            input_data=json.dumps(input_data) if input_data else None,
            output_data=json.dumps(output_data) if output_data else None,
            status=status,
            error_message=error,
        )
        db.session.add(entry)
        db.session.commit()

    def run(self, *args, **kwargs):
        raise NotImplementedError("Subclasses must implement run()")