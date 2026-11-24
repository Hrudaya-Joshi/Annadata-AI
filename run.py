"""
Entry point for the AI-Powered Food Waste Reduction & Donation Coordination System.
Run this file to start the Flask development server.
"""
from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)