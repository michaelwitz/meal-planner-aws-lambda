"""Flask application factory."""

import os
import logging
from datetime import datetime
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from .config import config
from .models.database import db

# Configure logging
log_level = logging.INFO
if os.getenv('DEBUG', '').lower() == 'true':
    log_level = logging.DEBUG

logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app(config_name=None):
    """Create and configure the Flask application.
    
    Args:
        config_name: Configuration to use (development, production, testing)
    
    Returns:
        Flask application instance
    """
    logger.info("Starting Flask app creation...")
    
    if config_name is None:
        # In Lambda, use production config
        if 'AWS_LAMBDA_FUNCTION_NAME' in os.environ:
            config_name = 'production'
        else:
            config_name = os.getenv('FLASK_ENV', 'development-local')
    
    logger.info(f"Using config: {config_name}")
    logger.info(f"Environment - IS_LOCAL: {os.getenv('IS_LOCAL', 'not set')}")
    logger.info(f"Environment - USE_LOCAL_DB: {os.getenv('USE_LOCAL_DB', 'not set')}")
    logger.info(f"Environment - RDS_PROXY_ENDPOINT: {os.getenv('RDS_PROXY_ENDPOINT', 'not set')[:20]}..." if os.getenv('RDS_PROXY_ENDPOINT') else "RDS_PROXY_ENDPOINT not set")
    
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    logger.info(f"Loaded configuration for {config_name}")
    
    # Initialize extensions
    logger.info("Initializing database...")
    try:
        db.init_app(app)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise
    
    CORS(app)
    JWTManager(app)
    logger.info("Extensions initialized")
    
    # Create tables (for development - in production use migrations)
    with app.app_context():
        # Import models to ensure they're registered
        from .models import entities
        
        # Only create tables in development
        if config_name == 'development':
            logger.info("Creating database tables...")
            try:
                db.create_all()
                logger.info("Database tables created")
            except Exception as e:
                logger.warning(f"Could not create tables (may already exist): {str(e)}")
    
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
    
    @app.route('/test')
    def test_endpoint():
        """Simple test endpoint that doesn't use database."""
        logger.info("Test endpoint called")
        return jsonify({
            'status': 'ok',
            'message': 'Lambda is responding!',
            'timestamp': datetime.utcnow().isoformat(),
            'environment': os.getenv('ENVIRONMENT', 'unknown'),
            'is_local': os.getenv('IS_LOCAL', 'not set'),
            'python_version': os.sys.version,
            'code_changed': '2025-08-20T19:39:37Z'
        })
    
    @app.route('/test-db')
    def test_db_endpoint():
        """Test endpoint that attempts database connection."""
        logger.info("Test DB endpoint called")
        try:
            from sqlalchemy import text
            logger.info("Attempting to execute test query...")
            
            result = db.session.execute(text('SELECT 1 as test, version() as db_version'))
            row = result.fetchone()
            
            logger.info(f"Database query successful: {row}")
            return jsonify({
                'status': 'ok',
                'message': 'Database connection successful!',
                'db_version': row.db_version if row else 'unknown',
                'timestamp': datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"Database test failed: {str(e)}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': 'Database connection failed',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }), 500
    
    logger.info("Flask app created successfully")
    return app
