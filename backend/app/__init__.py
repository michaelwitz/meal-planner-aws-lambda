"""Flask application factory."""

import os
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from .config import config
from .models.database import db


def create_app(config_name=None):
    """Create and configure the Flask application.
    
    Args:
        config_name: Configuration to use (development, production, testing)
    
    Returns:
        Flask application instance
    """
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    CORS(app)
    JWTManager(app)
    
    # Create tables (for development - in production use migrations)
    with app.app_context():
        # Import models to ensure they're registered
        from .models import entities
        
        # Create all tables
        db.create_all()
    
    # Register error handlers
    from werkzeug.exceptions import BadRequest
    from pydantic import ValidationError
    
    @app.errorhandler(BadRequest)
    def handle_bad_request(e):
        """Handle validation errors with proper status code."""
        # Check if this is a Pydantic validation error from flask-pydantic
        if hasattr(e, 'description') and 'validation error' in str(e.description).lower():
            return {'error': 'Validation Error', 'details': e.description}, 422
        return {'error': str(e.description)}, 400
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(e):
        """Handle Pydantic validation errors."""
        return {'error': 'Validation Error', 'details': e.errors()}, 422
    
    # Register blueprints
    from .blueprints.auth.routes import auth_bp
    
    app.register_blueprint(auth_bp, url_prefix=f"{app.config['API_PREFIX']}/auth")
    
    # TODO: Add more blueprints as they are created
    # from .blueprints.users.routes import users_bp
    # from .blueprints.meals.routes import meals_bp
    # app.register_blueprint(users_bp, url_prefix=f"{app.config['API_PREFIX']}/users")
    # app.register_blueprint(meals_bp, url_prefix=f"{app.config['API_PREFIX']}/meals")
    
    @app.route('/health')
    def health_check():
        """Health check endpoint."""
        return {'status': 'healthy'}, 200
    
    return app
