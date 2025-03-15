import os
import logging
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)

    # Security headers
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response

    # Error handlers
    @app.errorhandler(500)
    def internal_error(error):
        logger.exception("An internal error occurred")
        return jsonify(error=str(error)), 500

    @app.errorhandler(404)
    def not_found_error(error):
        logger.error(f"Page not found: {request.url}")
        return jsonify(error="Resource not found"), 404

    # Get database URL from environment, fail if not set
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL environment variable must be set")
        raise ValueError("DATABASE_URL environment variable must be set")

    # Configure Flask app
    app.config.update(
        SECRET_KEY=os.environ.get("SESSION_SECRET", "dev-key-please-change"),
        SQLALCHEMY_DATABASE_URI=database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={
            "pool_recycle": 300,
            "pool_pre_ping": True,
        }
    )

    logger.info("Application configuration loaded successfully")

    # Initialize extensions
    try:
        db.init_app(app)
        login_manager.init_app(app)
        login_manager.login_view = 'main.login'
        logger.info("Flask extensions initialized successfully")
    except Exception as e:
        logger.exception("Failed to initialize Flask extensions")
        raise

    with app.app_context():
        # Import models here to avoid circular imports
        from models import User, APIKey, Article

        try:
            # Create tables if they don't exist
            db.create_all()
            logger.info("Database tables created successfully")

            # Create admin user if it doesn't exist
            if not User.query.filter_by(username='admin').first():
                admin = User(username='admin', is_admin=True)
                admin.set_password('admin')
                db.session.add(admin)
                db.session.commit()
                logger.info("Admin user created successfully")

        except Exception as e:
            logger.exception("Database initialization error")
            raise

        # Test database connection
        try:
            db.session.execute(text('SELECT 1'))
            logger.info("Database connection test successful")
        except Exception as e:
            logger.exception("Database connection test failed")
            raise

        # Import and register blueprints
        try:
            from routes import main as main_blueprint
            app.register_blueprint(main_blueprint)
            logger.info("Blueprints registered successfully")
        except Exception as e:
            logger.exception("Failed to register blueprints")
            raise

    return app