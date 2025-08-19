"""JWT utility functions for authentication."""

from flask_jwt_extended import create_access_token, get_jwt_identity
from datetime import timedelta
from flask import current_app


def generate_token(user_id: int) -> tuple[str, int]:
    """
    Generate JWT access token for a user.
    
    Args:
        user_id: The user's database ID
        
    Returns:
        Tuple of (access_token, expires_in_seconds)
    """
    # Get from config (which gets from .env) - no fallback
    expires_in = current_app.config['JWT_ACCESS_TOKEN_EXPIRES']
    expires_delta = timedelta(seconds=expires_in)
    
    access_token = create_access_token(
        identity=str(user_id),  # JWT requires string identity
        expires_delta=expires_delta
    )
    
    return access_token, expires_in


def get_current_user_id() -> int:
    """
    Get the current authenticated user's ID from JWT.
    
    Returns:
        User ID from the JWT token
    """
    return int(get_jwt_identity())  # Convert string back to int
