"""User service for handling user-related business logic."""

from typing import Dict, Any
from app.models.entities import User
from app.models.database import db


def get_user_by_id(user_id: int) -> User:
    """Get a user by their ID.
    
    Args:
        user_id: The user's ID
        
    Returns:
        User: The user object
        
    Raises:
        404: If user not found
    """
    return User.query.get_or_404(user_id)


def update_user_profile(user: User, profile_data: Dict[str, Any]) -> User:
    """Update a user's profile information.
    
    Args:
        user: The user to update
        profile_data: Dictionary containing updated profile fields
        
    Returns:
        User: The updated user object
        
    Raises:
        ValueError: If invalid data is provided
    """
    # Update fields if they are present in the request
    if 'full_name' in profile_data:
        user.full_name = profile_data['full_name']
    
    if 'sex' in profile_data:
        user.sex = profile_data['sex']
    
    if 'address_line_1' in profile_data:
        user.address_line_1 = profile_data['address_line_1']
    
    if 'address_line_2' in profile_data:
        user.address_line_2 = profile_data['address_line_2']
    
    if 'city' in profile_data:
        user.city = profile_data['city']
    
    if 'state_province_code' in profile_data:
        user.state_province_code = profile_data['state_province_code']
    
    if 'country_code' in profile_data:
        user.country_code = profile_data['country_code'].upper()
    
    if 'postal_code' in profile_data:
        user.postal_code = profile_data['postal_code']
    
    if 'phone_number' in profile_data:
        user.phone_number = profile_data['phone_number']
    
    db.session.commit()
    return user
