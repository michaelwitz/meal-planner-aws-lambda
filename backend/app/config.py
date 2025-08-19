"""Flask application configuration."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file in project root
project_root = Path(__file__).parent.parent.parent  # Go up from app/ to backend/ to project root/
env_path = project_root / '.env'

# Check if .env exists - fail fast if not
if not env_path.exists():
    raise FileNotFoundError(f".env file not found at {env_path}. Please create it from .env.example")

load_dotenv(env_path)


class Config:
    """Base configuration - NO DEFAULTS FOR SECRETS."""
    
    # Flask - REQUIRED (no defaults)
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("FLASK_SECRET_KEY environment variable is not set")
    
    # JWT - REQUIRED (no defaults)
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    if not JWT_SECRET_KEY:
        raise ValueError("JWT_SECRET_KEY environment variable is not set")
    
    JWT_ACCESS_TOKEN_EXPIRES_STR = os.getenv('JWT_ACCESS_TOKEN_EXPIRES')
    if not JWT_ACCESS_TOKEN_EXPIRES_STR:
        raise ValueError("JWT_ACCESS_TOKEN_EXPIRES environment variable is not set")
    JWT_ACCESS_TOKEN_EXPIRES = int(JWT_ACCESS_TOKEN_EXPIRES_STR)
    
    # API - Hardcoded as part of application design
    API_PREFIX = '/api'
    
    # Common settings
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = os.getenv('SQLALCHEMY_ECHO', 'false').lower() == 'true'


class DevelopmentLocalConfig(Config):
    """Development with local Docker PostgreSQL."""
    DEBUG = True
    TESTING = False
    
    # Build PostgreSQL URI for local database
    db_user = os.getenv('LOCAL_DB_USER')
    db_pass = os.getenv('LOCAL_DB_PASSWORD')
    db_host = os.getenv('LOCAL_DB_HOST')
    db_port = os.getenv('LOCAL_DB_PORT')
    db_name = os.getenv('LOCAL_DB_NAME')
    
    if not all([db_user, db_pass, db_host, db_port, db_name]):
        raise ValueError("Missing required LOCAL_DB_* environment variables. Check your .env file.")
    
    # Standard PostgreSQL connection URI
    SQLALCHEMY_DATABASE_URI = f'postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}'


class DevelopmentCloudConfig(Config):
    """Development with cloud RDS Serverless v2 (direct connection via URI)."""
    DEBUG = True
    TESTING = False
    
    # Build PostgreSQL URI for RDS Serverless v2
    # NOTE: We use standard PostgreSQL connection, NOT Data API
    db_user = os.getenv('DB_USER')
    db_pass = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST')  # RDS cluster endpoint
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME')
    
    if not all([db_user, db_pass, db_host, db_name]):
        raise ValueError("Missing required DB_* environment variables for cloud database. Check your .env file.")
    
    # Standard PostgreSQL connection URI - works with RDS Serverless v2
    SQLALCHEMY_DATABASE_URI = f'postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}'


class TestingConfig(Config):
    """Testing configuration - uses cloud database."""
    DEBUG = True
    TESTING = True
    
    # Testing uses cloud RDS with standard PostgreSQL connection
    db_user = os.getenv('DB_USER')
    db_pass = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('TEST_DB_NAME', os.getenv('DB_NAME'))  # Can use separate test DB
    
    if not all([db_user, db_pass, db_host, db_name]):
        raise ValueError("Missing required DB_* environment variables for test database. Check your .env file.")
    
    SQLALCHEMY_DATABASE_URI = f'postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}'


class ProductionConfig(Config):
    """Production configuration - Lambda environment."""
    DEBUG = False
    TESTING = False
    
    # In Lambda, database connection is handled differently
    # The database.py module will handle this via RDS Proxy
    # This is just a placeholder
    SQLALCHEMY_DATABASE_URI = 'will-be-set-by-lambda'


# Configuration dictionary
config = {
    'development-local': DevelopmentLocalConfig,
    'development-cloud': DevelopmentCloudConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentLocalConfig  # Default to local development
}
