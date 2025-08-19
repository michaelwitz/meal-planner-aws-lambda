"""
Test database configuration for local Docker PostgreSQL testing.

This module provides configuration for the local Docker PostgreSQL test database.

All sensitive information (URLs, passwords) should be stored in .env file.

Usage:
    pytest  # Uses local Docker database
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file in project root (parent directory)
project_root = Path(__file__).parent.parent.parent  # Go up from tests/ to backend/ to project root/
env_path = project_root / '.env'
load_dotenv(env_path)


@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    name: str
    url: str
    description: str
    
    def __str__(self):
        return f"{self.name}: {self.description}"


class TestDatabaseConfig:
    """Manages test database configuration."""
    
    @classmethod
    def _get_local_config(cls) -> DatabaseConfig:
        """Get local database configuration from environment."""
        url = os.getenv('TEST_DATABASE_URL_LOCAL')
        if not url:
            raise ValueError(
                "TEST_DATABASE_URL_LOCAL not found in environment. "
                "Please set it in your .env file."
            )
        
        return DatabaseConfig(
            name="local",
            url=url,
            description="Local Docker PostgreSQL database"
        )
    
    @classmethod
    def get_config(cls) -> DatabaseConfig:
        """
        Get database configuration for local testing.
        
        Returns:
            DatabaseConfig object for the local test database.
        
        Raises:
            ValueError: If configuration is missing.
        """
        config = cls._get_local_config()
        
        print(f"\n🗄️  Using {config.name} database for testing")
        print(f"   {config.description}")
        
        return config
    
    @classmethod
    def get_database_url(cls) -> str:
        """
        Get database URL for local testing.
        
        Returns:
            Database URL string
        """
        return cls.get_config().url
    
    @classmethod
    def validate_connection(cls) -> bool:
        """
        Validate that we can connect to the local test database.
        
        Returns:
            True if connection successful, raises exception otherwise
        """
        from sqlalchemy import create_engine, text
        from sqlalchemy.exc import OperationalError
        
        config = cls.get_config()
        engine = create_engine(config.url)
        
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                print(f"   ✅ Successfully connected to {config.name} database")
                return True
        except OperationalError as e:
            print(f"   ❌ Failed to connect to {config.name} database")
            raise e
        finally:
            engine.dispose()


# Convenience function for quick access
def get_test_database_url() -> str:
    """Get test database URL for local testing."""
    return TestDatabaseConfig.get_database_url()
