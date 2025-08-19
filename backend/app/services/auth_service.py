"""Authentication service for user registration and login."""

import bcrypt
from sqlalchemy.exc import IntegrityError
from app.models.database import db
from app.models.entities import User
from app.schemas.user_schemas import UserRegisterSchema, UserLoginSchema
from app.utils.jwt_utils import generate_token


class AuthService:
    """Service class for authentication operations."""
    
    @staticmethod
    def register_user(user_data: UserRegisterSchema) -> User:
        """
        Register a new user.
        
        Args:
            user_data: Validated user registration data
            
        Returns:
            Created User object
            
        Raises:
            ValueError: If username or email already exists
        """
        # Check if user already exists
        existing_user = User.query.filter(
            (User.email == user_data.email) | 
            (User.username == user_data.username)
        ).first()
        
        if existing_user:
            if existing_user.email == user_data.email:
                raise ValueError("Email already registered")
            else:
                raise ValueError("Username already taken")
        
        # Hash the password
        password_hash = bcrypt.hashpw(
            user_data.password.encode('utf-8'), 
            bcrypt.gensalt()
        ).decode('utf-8')
        
        # Create new user
        new_user = User(
            email=user_data.email,
            username=user_data.username,
            password_hash=password_hash,
            full_name=user_data.full_name,
            sex=user_data.sex.value,
            phone_number=user_data.phone_number,
            address_line_1=user_data.address_line_1,
            address_line_2=user_data.address_line_2,
            city=user_data.city,
            state_province_code=user_data.state_province_code,
            country_code=user_data.country_code,
            postal_code=user_data.postal_code
        )
        
        try:
            db.session.add(new_user)
            db.session.commit()
            return new_user
        except IntegrityError as e:
            db.session.rollback()
            raise ValueError("Failed to create user") from e
    
    @staticmethod
    def register_user_with_token(user_data: UserRegisterSchema) -> tuple[User, str, int]:
        """
        Register a new user and generate JWT token for immediate login.
        
        Args:
            user_data: Validated user registration data
            
        Returns:
            Tuple of (User, access_token, expires_in)
            
        Raises:
            ValueError: If username or email already exists
        """
        # Register the user
        user = AuthService.register_user(user_data)
        
        # Generate token for immediate login
        access_token, expires_in = generate_token(user.id)
        
        return user, access_token, expires_in
    
    @staticmethod
    def authenticate_user(login_data: UserLoginSchema) -> tuple[User, str, int]:
        """
        Authenticate a user and generate JWT token.
        
        Args:
            login_data: Login credentials (email/username and password)
            
        Returns:
            Tuple of (User, access_token, expires_in)
            
        Raises:
            ValueError: If credentials are invalid
        """
        # Find user by email or username
        user = User.query.filter(
            (User.email == login_data.login) | 
            (User.username == login_data.login)
        ).first()
        
        if not user:
            raise ValueError("Invalid credentials")
        
        # Verify password
        if not bcrypt.checkpw(
            login_data.password.encode('utf-8'),
            user.password_hash.encode('utf-8')
        ):
            raise ValueError("Invalid credentials")
        
        # Generate JWT token
        access_token, expires_in = generate_token(user.id)
        
        return user, access_token, expires_in
    
    @staticmethod
    def get_user_by_id(user_id: int) -> User:
        """
        Get user by ID.
        
        Args:
            user_id: User's database ID
            
        Returns:
            User object
            
        Raises:
            ValueError: If user not found
        """
        user = User.query.get(user_id)
        if not user:
            raise ValueError("User not found")
        return user
