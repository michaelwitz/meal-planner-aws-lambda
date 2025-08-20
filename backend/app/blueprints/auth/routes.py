"""Authentication routes for user registration, login, and profile."""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.utils.validation import validate_with_422 as validate
from app.schemas.user_schemas import (
    UserRegisterSchema, 
    UserLoginSchema, 
    UserResponseSchema,
    TokenResponseSchema
)
from app.services.auth_service import AuthService

# Create blueprint
auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
@validate()
def register(body: UserRegisterSchema):
    """
    Register a new user.
    
    Request Body:
        UserRegisterSchema with all required fields
        
    Returns:
        201: User created successfully with JWT token
        400: Validation error or user already exists
    """
    try:
        # Register user and generate token for immediate login
        user, access_token, expires_in = AuthService.register_user_with_token(body)
        
        # Create response
        user_response = UserResponseSchema.model_validate(user)
        token_response = TokenResponseSchema(
            accessToken=access_token,
            tokenType="bearer",
            expiresIn=expires_in,
            user=user_response
        )
        
        return jsonify(token_response.model_dump()), 201
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Registration failed"}), 500


@auth_bp.route('/login', methods=['POST'])
@validate()
def login(body: UserLoginSchema):
    """
    Login user with email/username and password.
    
    Request Body:
        UserLoginSchema with login (email or username) and password
        
    Returns:
        200: Login successful with JWT token
        401: Invalid credentials
    """
    try:
        # Authenticate user
        user, access_token, expires_in = AuthService.authenticate_user(body)
        
        # Create response
        user_response = UserResponseSchema.model_validate(user)
        token_response = TokenResponseSchema(
            accessToken=access_token,
            tokenType="bearer",
            expiresIn=expires_in,
            user=user_response
        )
        
        return jsonify(token_response.model_dump()), 200
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 401
    except Exception as e:
        return jsonify({"error": "Login failed"}), 500


@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """
    Get current user's profile.
    
    Requires JWT token in Authorization header.
    
    Returns:
        200: User profile data
        401: Unauthorized (invalid/missing token)
        404: User not found
    """
    try:
        # Get current user ID from JWT
        user_id = get_jwt_identity()
        
        # Get user data
        user = AuthService.get_user_by_id(user_id)
        
        # Create response
        user_response = UserResponseSchema.from_orm(user)
        
        return jsonify(user_response.model_dump(by_alias=True)), 200
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": "Failed to retrieve profile"}), 500


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    Logout user (client should discard JWT token).
    
    Requires JWT token in Authorization header.
    
    Returns:
        200: Logout successful
    """
    # In a stateless JWT system, logout is handled client-side
    # The client should discard the token
    # For enhanced security, you could implement a token blacklist
    
    return jsonify({"message": "Logout successful"}), 200
