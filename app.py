import os
import logging
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

logging.basicConfig(level=logging.DEBUG)

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
        logging.error(f"Internal Server Error: {str(error)}")
        return jsonify(error=str(error)), 500

    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify(error="Resource not found"), 404

    # Get database URL from environment, fail if not set
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
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

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'

    with app.app_context():
        # Import models here to avoid circular imports
        from models import User, APIKey, Article

        try:
            # Create tables if they don't exist
            db.create_all()
            logging.info("Database tables created successfully")

            # Create admin user if it doesn't exist
            if not User.query.filter_by(username='admin').first():
                admin = User(username='admin', is_admin=True)
                admin.set_password('admin')
                db.session.add(admin)
                db.session.commit()
                logging.info("Admin user created successfully")

        except Exception as e:
            logging.error(f"Database initialization error: {str(e)}")
            raise

        # Test database connection
        try:
            db.session.execute(text('SELECT 1'))
            logging.info("Database connection test successful")
        except Exception as e:
            logging.error(f"Database connection test failed: {str(e)}")
            raise

        # Import and register blueprints
        from routes import main as main_blueprint
        app.register_blueprint(main_blueprint)

    return app