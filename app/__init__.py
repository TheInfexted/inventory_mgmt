from flask import Flask
from app.config import Config
from app.extensions import db, migrate
from flask_login import LoginManager

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Register routes
    from app import routes
    app.register_blueprint(routes.bp)

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp)

    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp)

    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(id):
        from app.models import User
        return User.query.get(int(id))

    return app