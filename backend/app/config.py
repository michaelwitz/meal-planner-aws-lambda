"""Flask application configuration."""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
log_level = logging.INFO
if os.getenv('DEBUG', '').lower() == 'true':
    log_level = logging.DEBUG

logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Detect if we're running in AWS Lambda
is_lambda = 'AWS_LAMBDA_FUNCTION_NAME' in os.environ
logger.info(f"Running in Lambda: {is_lambda}")
if is_lambda:
    logger.info(f"Lambda function name: {os.getenv('AWS_LAMBDA_FUNCTION_NAME')}")

if not is_lambda:
    # Running locally - try .env.dev first, fall back to .env
    project_root = Path(__file__).parent.parent.parent
    env_dev_path = project_root / '.env.dev'
    env_path = project_root / '.env'
    
    if env_dev_path.exists():
        load_dotenv(env_dev_path)
        logger.info(".env.dev file loaded for local development")
    elif env_path.exists():
        load_dotenv(env_path)
        logger.info(".env file loaded (no .env.dev found)")
    else:
        raise FileNotFoundError(
            "\n\nEnvironment configuration error:\n"
            "  - Not running in AWS Lambda (AWS_LAMBDA_FUNCTION_NAME not set)\n"
            "  - Neither .env.dev nor .env found in project root\n\n"
            "To fix this:\n"
            "  1. Copy .env.example to .env.dev\n"
            "  2. Fill in your development configuration values\n"
            "  3. Ensure you're running from the project root\n"
            "\nNote: Use .env.dev for development, .env is only for Lambda deployments\n"
        )


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


# Lambda configurations - Use RDS Proxy (DB_HOST is set to RDS_PROXY_ENDPOINT in serverless.yml)
if is_lambda:
    class ProductionConfig(Config):
        """Production configuration - Lambda environment via RDS Proxy."""
        DEBUG = False
        TESTING = False
        
        # Lambda connects to RDS via RDS Proxy endpoint
        # DB_HOST is set to RDS_PROXY_ENDPOINT in serverless.yml
        db_user = os.getenv('DB_USER')
        db_pass = os.getenv('DB_PASSWORD')
        db_host = os.getenv('DB_HOST')  # This is RDS_PROXY_ENDPOINT from serverless.yml
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME')
        
        logger.info(f"Lambda DB Config:")
        logger.info(f"  Host: {db_host[:30] if db_host else 'NOT SET'}...")
        logger.info(f"  Database: {db_name if db_name else 'NOT SET'}")
        logger.info(f"  User: {db_user if db_user else 'NOT SET'}")
        logger.info(f"  Port: {db_port}")
        
        if not all([db_user, db_pass, db_host, db_name]):
            missing = []
            if not db_user: missing.append('DB_USER')
            if not db_pass: missing.append('DB_PASSWORD') 
            if not db_host: missing.append('DB_HOST')
            if not db_name: missing.append('DB_NAME')
            logger.error(f"Missing required environment variables: {missing}")
            raise ValueError(
                f"Missing required DB environment variables in Lambda: {missing}. "
                "Check serverless.yml environment configuration."
            )
        
        # PostgreSQL connection URI via RDS Proxy
        SQLALCHEMY_DATABASE_URI = f'postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}'
        logger.info(f"Lambda database URI configured successfully")
    
    # Testing is just production with debug enabled (both use RDS Proxy)
    class TestingConfig(ProductionConfig):
        """Testing configuration - Lambda test stage via RDS Proxy."""
        DEBUG = True
        TESTING = True
    
    # Create placeholder classes for local configs (never used in Lambda)
    class DevelopmentLocalConfig(Config):
        pass
    
    class DevelopmentCloudConfig(Config):
        pass

# Local development configurations - Direct connections (no RDS Proxy)
else:
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
        """Development with cloud RDS Serverless v2 (direct connection, no proxy)."""
        DEBUG = True
        TESTING = False
        
        # Direct connection to RDS cluster endpoint (not proxy)
        db_user = os.getenv('DB_USER')
        db_pass = os.getenv('DB_PASSWORD')
        db_host = os.getenv('DB_HOST')  # RDS cluster endpoint (direct)
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME')
        
        if not all([db_user, db_pass, db_host, db_name]):
            raise ValueError("Missing required DB_* environment variables for cloud database. Check your .env file.")
        
        # Standard PostgreSQL connection URI - direct to RDS cluster
        SQLALCHEMY_DATABASE_URI = f'postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}'
    
    # Create placeholder classes for Lambda configs (never used locally)
    class ProductionConfig(Config):
        pass
    
    class TestingConfig(Config):
        """Testing configuration that works in both Lambda and local environments."""
        DEBUG = True
        TESTING = True
        
        # Build PostgreSQL URI for test database
        db_user = os.getenv('DB_USER')
        db_pass = os.getenv('DB_PASSWORD')
        db_host = os.getenv('DB_HOST')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME')
        
        if not all([db_user, db_pass, db_host, db_name]):
            raise ValueError("Missing required DB_* environment variables for testing. Check your test configuration.")
        
        # In Lambda, we need to get the database connection details from the Lambda environment
        # In local dev, we get them from the test environment variables in conftest.py
        SQLALCHEMY_DATABASE_URI = f'postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}'
        
        # Log test database configuration
        logger.info(f"Test DB Config (in {'Lambda' if is_lambda else 'Local'} mode):")
        logger.info(f"  Host: {db_host}")
        logger.info(f"  Database: {db_name}")
        logger.info(f"  User: {db_user}")
        logger.info(f"  Port: {db_port}")


def get_config(config_name=None):
    """Get configuration class based on environment.
    
    This function lazily loads only the configuration class that's needed,
    avoiding errors from missing environment variables in unused configs.
    """
    if config_name is None:
        # Determine config based on environment
        if is_lambda:
            config_name = 'production'
        else:
            # Check USE_LOCAL_DB to determine local vs cloud
            use_local = os.getenv('USE_LOCAL_DB', 'true').lower() == 'true'
            config_name = 'development-local' if use_local else 'development-cloud'
    
    # Only evaluate the config class we need
    if config_name == 'production':
        # Lambda environment - skip local config classes
        return ProductionConfig
    elif config_name == 'development-local':
        # Local development - skip Lambda config
        return DevelopmentLocalConfig
    elif config_name == 'development-cloud':
        # Cloud development - skip local config
        return DevelopmentCloudConfig
    elif config_name == 'testing':
        return TestingConfig
    else:
        # Default to local development
        return DevelopmentLocalConfig

# Configuration dictionary
config = {
    'development-local': DevelopmentLocalConfig,
    'development-cloud': DevelopmentCloudConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentLocalConfig
}
