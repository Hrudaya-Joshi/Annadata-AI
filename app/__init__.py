import os
from flask import Flask
from app.config import Config
from app.extensions import db, login_manager, migrate

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')


def create_app(config_class=Config, config_override=None):
    app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
    app.config.from_object(config_class)
    if config_override:
        app.config.update(config_override)

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    # Register all Blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.restaurant import restaurant_bp
    from app.routes.ngo import ngo_bp
    from app.routes.volunteer import volunteer_bp
    from app.routes.admin import admin_bp
    from app.routes.api import api_bp
    from app.routes.passport import passport_bp
    from app.routes.missions import missions_bp
    from app.routes.intelligence import intelligence_bp
    from app.routes.impact import impact_bp
    from app.routes.map import map_bp
    from app.routes.notifications import notifications_bp
    from app.routes.profile import profile_bp
    from app.routes.assistant import assistant_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(restaurant_bp)
    app.register_blueprint(ngo_bp)
    app.register_blueprint(volunteer_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(passport_bp)
    app.register_blueprint(missions_bp)
    app.register_blueprint(intelligence_bp)
    app.register_blueprint(impact_bp)
    app.register_blueprint(map_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(assistant_bp)

    from app.models import User, Notification
    from flask_login import current_user
    from datetime import datetime

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.context_processor
    def inject_global_data():
        unread_notifications = 0
        if current_user.is_authenticated:
            try:
                unread_notifications = Notification.query.filter_by(
                    user_id=current_user.id, is_read=False
                ).count()
            except Exception:
                unread_notifications = 0

        return {
            "app_name": "ANNADATA AI",
            "app_tagline": "Every Meal Matters. Every Rescue Counts.",
            "unread_notifications": unread_notifications,
            "datetime": datetime,
            "now": datetime.utcnow()
        }

    return app
