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
    fullName: str = Field(..., min_length=1, max_length=255)
    sex: SexEnum  # Required
    phoneNumber: Optional[str] = Field(None, max_length=50)
    addressLine1: str = Field(..., min_length=1, max_length=255)  # Required
    addressLine2: Optional[str] = Field(None, max_length=255)
    city: str = Field(..., min_length=1, max_length=100)  # Required
    stateProvinceCode: str = Field(..., min_length=1, max_length=10)  # Required
    countryCode: str = Field(..., min_length=2, max_length=2)  # Required
    postalCode: str = Field(..., min_length=1, max_length=20)  # Required

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

    @validator('countryCode')
    def country_code_uppercase(cls, v):
        """Ensure country code is uppercase."""
        return v.upper()


class UserLoginSchema(BaseModel):
    """Schema for user login."""
    login: str = Field(..., description="Email or username")
    password: str = Field(..., min_length=1)


class UserUpdateSchema(BaseModel):
    """Schema for updating user profile."""
    fullName: Optional[str] = Field(None, min_length=1, max_length=255)
    sex: Optional[SexEnum] = None
    phoneNumber: Optional[str] = Field(None, max_length=50)
    addressLine1: Optional[str] = Field(None, min_length=1, max_length=255)
    addressLine2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, min_length=1, max_length=100)
    stateProvinceCode: Optional[str] = Field(None, min_length=2, max_length=2)
    countryCode: Optional[str] = Field(None, min_length=2, max_length=2)
    postalCode: Optional[str] = Field(None, min_length=1, max_length=20)

    @validator('countryCode')
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
    fullName: str
    sex: str  # Required in response
    phoneNumber: Optional[str] = None
    addressLine1: str  # Required in response
    addressLine2: Optional[str] = None
    city: str  # Required in response
    stateProvinceCode: str  # Required in response
    countryCode: str  # Required in response
    postalCode: str  # Required in response
    createdAt: datetime
    updatedAt: datetime

    class Config:
        """Pydantic configuration."""
        from_attributes = True  # This allows compatibility with SQLAlchemy models


class PasswordChangeSchema(BaseModel):
    """Schema for password change request."""
    currentPassword: str = Field(..., min_length=1)
    newPassword: str = Field(..., min_length=8)
    
    @validator('newPassword')
    def password_strength(cls, v):
        """Basic password strength validation."""
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isalpha() for char in v):
            raise ValueError('Password must contain at least one letter')
        return v


class TokenResponseSchema(BaseModel):
    """Schema for JWT token response."""
    accessToken: str
    tokenType: str = "bearer"
    expiresIn: int  # seconds
    user: UserResponseSchema
