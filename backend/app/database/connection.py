"""
Database connection module for AWS Lambda with RDS Serverless v2.

This module handles database connections optimized for Lambda's execution model
and RDS Serverless v2's auto-pause feature.
"""
import os
import json
import time
import logging
from typing import Optional, Dict, Any
from contextlib import contextmanager

import boto3
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from sqlalchemy.exc import OperationalError

logger = logging.getLogger(__name__)

# Global variables for connection reuse within Lambda container
_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker] = None


def get_db_credentials() -> Dict[str, Any]:
    """
    Retrieve database credentials from environment variables or AWS Secrets Manager.
    
    Returns:
        Dict containing host, port, database, username, and password
    """
    # Check if we should use Secrets Manager
    if os.environ.get('USE_SECRETS_MANAGER') == 'true':
        secret_name = os.environ.get('DB_SECRET_NAME', 'meal-planner/rds/credentials')
        region = os.environ.get('AWS_REGION', 'us-east-1')
        
        logger.info(f"Fetching credentials from Secrets Manager: {secret_name}")
        
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name=region
        )
        
        try:
            response = client.get_secret_value(SecretId=secret_name)
            secret = json.loads(response['SecretString'])
            
            return {
                'host': secret['host'],
                'port': secret.get('port', 5432),
                'database': secret['dbname'],
                'username': secret['username'],
                'password': secret['password']
            }
        except Exception as e:
            logger.error(f"Error fetching secret: {e}")
            raise
    
    # Use environment variables (default for development)
    return {
        'host': os.environ['DB_HOST'],
        'port': os.environ.get('DB_PORT', 5432),
        'database': os.environ['DB_NAME'],
        'username': os.environ['DB_USER'],
        'password': os.environ['DB_PASSWORD']
    }


def create_db_engine(max_retries: int = 3, retry_delay: int = 5) -> Engine:
    """
    Create SQLAlchemy engine with Lambda-optimized settings.
    
    Handles RDS Serverless v2 cold starts (15-30 second wake-up time).
    
    Args:
        max_retries: Maximum number of connection attempts
        retry_delay: Delay between retries in seconds
        
    Returns:
        SQLAlchemy Engine instance
    """
    creds = get_db_credentials()
    
    # Build connection URL
    db_url = (
        f"postgresql://{creds['username']}:{creds['password']}"
        f"@{creds['host']}:{creds['port']}/{creds['database']}"
    )
    
    # Lambda-optimized connection arguments
    connect_args = {
        "connect_timeout": 10,  # Connection timeout in seconds
        "options": "-c statement_timeout=60000"  # 60 second statement timeout
    }
    
    # Try to connect with retries (for RDS Serverless v2 wake-up)
    for attempt in range(max_retries):
        try:
            logger.info(f"Creating database engine (attempt {attempt + 1}/{max_retries})")
            
            engine = create_engine(
                db_url,
                poolclass=NullPool,  # Critical for Lambda - no connection pooling
                echo=os.environ.get('SQLALCHEMY_ECHO', 'false').lower() == 'true',
                connect_args=connect_args
            )
            
            # Test the connection
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            
            logger.info("Database connection successful")
            return engine
            
        except OperationalError as e:
            logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
            
            if attempt < max_retries - 1:
                # RDS Serverless v2 might be waking up from pause
                logger.info(f"Waiting {retry_delay} seconds before retry...")
                time.sleep(retry_delay)
            else:
                logger.error("Max retries reached, connection failed")
                raise
    
    raise Exception("Failed to create database engine")


def get_engine() -> Engine:
    """
    Get or create the global database engine.
    
    Reuses engine within the same Lambda container for efficiency.
    
    Returns:
        SQLAlchemy Engine instance
    """
    global _engine
    
    if _engine is None:
        _engine = create_db_engine()
    
    return _engine


def get_session_factory() -> sessionmaker:
    """
    Get or create the session factory.
    
    Returns:
        SQLAlchemy sessionmaker instance
    """
    global _SessionLocal
    
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine()
        )
    
    return _SessionLocal


def get_session() -> Session:
    """
    Create a new database session.
    
    Returns:
        SQLAlchemy Session instance
    """
    SessionLocal = get_session_factory()
    return SessionLocal()


@contextmanager
def get_db():
    """
    Context manager for database sessions.
    
    Ensures proper session cleanup even if an error occurs.
    
    Yields:
        SQLAlchemy Session instance
    """
    db = get_session()
    try:
        yield db
        db.commit()
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def close_engine():
    """
    Close the global engine and clear references.
    
    Useful for cleanup in tests or when Lambda container is being recycled.
    """
    global _engine, _SessionLocal
    
    if _engine:
        _engine.dispose()
        _engine = None
    
    _SessionLocal = None
    logger.info("Database engine closed")


# Lambda warmup check
def is_lambda_warm() -> bool:
    """
    Check if this is a warm Lambda invocation.
    
    Returns:
        True if engine already exists (warm), False otherwise (cold)
    """
    return _engine is not None
