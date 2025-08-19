"""Pydantic schemas for user-related operations."""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
from enum import Enum


class SexEnum(str, Enum):
    """Sex enumeration matching database model."""
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"


class UserRegisterSchema(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=1, max_length=255)
    sex: SexEnum  # Required
    phone_number: Optional[str] = Field(None, max_length=50)
    address_line_1: str = Field(..., min_length=1, max_length=255)  # Required
    address_line_2: Optional[str] = Field(None, max_length=255)
    city: str = Field(..., min_length=1, max_length=100)  # Required
    state_province_code: str = Field(..., min_length=1, max_length=10)  # Required
    country_code: str = Field(..., min_length=2, max_length=2)  # Required
    postal_code: str = Field(..., min_length=1, max_length=20)  # Required

    @validator('username')
    def username_valid_chars(cls, v):
        """Validate username contains only alphanumeric characters, underscores, and hyphens."""
        allowed_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-')
        if not all(char in allowed_chars for char in v):
            raise ValueError('Username must contain only letters, numbers, underscores, and hyphens')
        return v

    @validator('password')
    def password_strength(cls, v):
        """Basic password strength validation."""
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isalpha() for char in v):
            raise ValueError('Password must contain at least one letter')
        return v

    @validator('country_code')
    def country_code_uppercase(cls, v):
        """Ensure country code is uppercase."""
        return v.upper()


class UserLoginSchema(BaseModel):
    """Schema for user login."""
    login: str = Field(..., description="Email or username")
    password: str = Field(..., min_length=1)


class UserUpdateSchema(BaseModel):
    """Schema for updating user profile."""
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    sex: Optional[SexEnum] = None
    phone_number: Optional[str] = Field(None, max_length=50)
    address_line_1: Optional[str] = Field(None, min_length=1, max_length=255)
    address_line_2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, min_length=1, max_length=100)
    state_province_code: Optional[str] = Field(None, min_length=1, max_length=10)
    country_code: Optional[str] = Field(None, min_length=2, max_length=2)
    postal_code: Optional[str] = Field(None, min_length=1, max_length=20)

    @validator('country_code')
    def country_code_uppercase(cls, v):
        """Ensure country code is uppercase if provided."""
        if v:
            return v.upper()
        return v


class UserResponseSchema(BaseModel):
    """Schema for user response (without password)."""
    id: int
    email: str
    username: str
    full_name: str
    sex: str  # Required in response
    phone_number: Optional[str] = None
    address_line_1: str  # Required in response
    address_line_2: Optional[str] = None
    city: str  # Required in response
    state_province_code: str  # Required in response
    country_code: str  # Required in response
    postal_code: str  # Required in response
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic configuration."""
        from_attributes = True  # This allows compatibility with SQLAlchemy models


class TokenResponseSchema(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserResponseSchema
