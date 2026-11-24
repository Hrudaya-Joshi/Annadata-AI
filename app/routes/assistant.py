from flask import Blueprint, request, jsonify
from flask_login import current_user
from app.agents.rescue_assistant_agent import RescueAssistantAgent

assistant_bp = Blueprint('assistant', __name__, url_prefix='/api/assistant')


@assistant_bp.route('/chat', methods=['POST'])
def chat():
    data = request.get_json() or {}
    message = data.get('message', '').strip()
    if not message:
        return jsonify({"error": "Empty message"}), 400

    agent = RescueAssistantAgent()
    result = agent.run(current_user, message)
    return jsonify(result), 200
