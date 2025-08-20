"""SQLAlchemy model entities for the meal planner application."""

import bcrypt
from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy import (
    Column, String, Float, Boolean, DateTime, Date, Integer,
    ForeignKey, Text, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .database import db


class SexEnum(str, Enum):
    """Enumeration for user sex."""
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"


class FoodCategoryEnum(str, Enum):
    """Enumeration for food categories."""
    MEAT = "MEAT"
    FISH = "FISH"
    GRAIN = "GRAIN"
    VEGETABLE = "VEGETABLE"
    FRUIT = "FRUIT"
    DAIRY = "DAIRY"
    DAIRY_ALTERNATIVE = "DAIRY_ALTERNATIVE"
    FAT = "FAT"
    NIGHTSHADES = "NIGHTSHADES"
    OIL = "OIL"
    SPICE_HERB = "SPICE_HERB"
    SWEETENER = "SWEETENER"
    CONDIMENT = "CONDIMENT"
    SNACK = "SNACK"
    BEVERAGE = "BEVERAGE"
    OTHER = "OTHER"


class User(db.Model):
    """User model for authentication and profile information."""
    __tablename__ = 'USER'
    
    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Authentication fields
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Profile fields
    fullName: Mapped[str] = mapped_column('full_name', String(255), nullable=False)
    sex: Mapped[str] = mapped_column(String(20), nullable=False)  # MALE, FEMALE, OTHER - Required
    phoneNumber: Mapped[Optional[str]] = mapped_column('phone_number', String(50), nullable=True)
    
    # Address fields
    addressLine1: Mapped[str] = mapped_column('address_line_1', String(255), nullable=False)  # Required
    addressLine2: Mapped[Optional[str]] = mapped_column('address_line_2', String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)  # Required
    stateProvinceCode: Mapped[str] = mapped_column('state_province_code', String(10), nullable=False)  # Required
    countryCode: Mapped[str] = mapped_column('country_code', String(2), nullable=False)  # Required
    postalCode: Mapped[str] = mapped_column('postal_code', String(20), nullable=False)  # Required
    
    # Timestamps
    createdAt: Mapped[datetime] = mapped_column('created_at', DateTime, nullable=False, default=datetime.utcnow)
    updatedAt: Mapped[datetime] = mapped_column('updated_at', DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    favorite_foods = relationship('FoodUserLikes', back_populates='user', cascade='all, delete-orphan')
    meals = relationship('UserMeal', back_populates='user', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def update_password(self, new_password: str):
        """Update user's password with proper hashing.
        
        Args:
            new_password: The new password to set
        """
        self.password_hash = bcrypt.hashpw(
            new_password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')


class Food(db.Model):
    """Food model for storing food items and their nutritional information."""
    __tablename__ = 'FOOD_CATALOG'
    
    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Food information
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # Uses FoodCategoryEnum values
    
    # Nutritional information (per serving)
    calories: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    protein: Mapped[float] = mapped_column(Float, nullable=False, default=0)  # in grams
    carbs: Mapped[float] = mapped_column(Float, nullable=False, default=0)    # in grams
    fat: Mapped[float] = mapped_column(Float, nullable=False, default=0)      # in grams
    fiber: Mapped[float] = mapped_column(Float, nullable=False, default=0)    # in grams
    
    # Serving information
    serving_size: Mapped[str] = mapped_column(String(100), nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Health information
    non_inflammatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user_likes = relationship('FoodUserLikes', back_populates='food', cascade='all, delete-orphan')
    meal_ingredients = relationship('MealIngredients', back_populates='food', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Food {self.name}>'


class Meal(db.Model):
    """Meal model for storing meal combinations."""
    __tablename__ = 'MEAL'
    
    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Meal information
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Aggregated nutritional information
    total_calories: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    total_protein: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    total_carbs: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    total_fat: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    
    # Preparation information
    prep_time: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # in minutes
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user_meals = relationship('UserMeal', back_populates='meal', cascade='all, delete-orphan')
    ingredients = relationship('MealIngredients', back_populates='meal', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Meal {self.name}>'


class FoodUserLikes(db.Model):
    """Association table for user's favorite/liked foods."""
    __tablename__ = 'FOOD_USER_LIKES'
    
    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Foreign keys
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('USER.id', ondelete='CASCADE'), nullable=False)
    food_id: Mapped[int] = mapped_column(Integer, ForeignKey('FOOD_CATALOG.id', ondelete='CASCADE'), nullable=False)
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    user = relationship('User', back_populates='favorite_foods')
    food = relationship('Food', back_populates='user_likes')
    
    # Unique constraint to prevent duplicate likes
    __table_args__ = (
        UniqueConstraint('user_id', 'food_id', name='uq_user_food_like'),
        Index('ix_food_user_likes_user_id', 'user_id'),
        Index('ix_food_user_likes_food_id', 'food_id'),
    )
    
    def __repr__(self):
        return f'<FoodUserLikes user_id={self.user_id} food_id={self.food_id}>'


class UserMeal(db.Model):
    """Association table for user's meals with date and meal number."""
    __tablename__ = 'USER_MEAL'
    
    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Foreign keys
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('USER.id', ondelete='CASCADE'), nullable=False)
    meal_id: Mapped[int] = mapped_column(Integer, ForeignKey('MEAL.id', ondelete='CASCADE'), nullable=False)
    
    # Meal scheduling
    date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    meal_number: Mapped[int] = mapped_column(Integer, nullable=False)  # 1=breakfast, 2=lunch, 3=dinner, 4=snack, etc.
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    user = relationship('User', back_populates='meals')
    meal = relationship('Meal', back_populates='user_meals')
    
    # Composite index for efficient queries
    __table_args__ = (
        Index('ix_user_meal_user_date', 'user_id', 'date'),
        Index('ix_user_meal_date_meal_number', 'date', 'meal_number'),
    )
    
    def __repr__(self):
        return f'<UserMeal user_id={self.user_id} meal_id={self.meal_id} date={self.date}>'


class MealIngredients(db.Model):
    """Association table for meal ingredients with quantities."""
    __tablename__ = 'MEAL_INGREDIENTS'
    
    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Foreign keys
    meal_id: Mapped[int] = mapped_column(Integer, ForeignKey('MEAL.id', ondelete='CASCADE'), nullable=False)
    food_id: Mapped[int] = mapped_column(Integer, ForeignKey('FOOD_CATALOG.id', ondelete='CASCADE'), nullable=False)
    
    # Ingredient details
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    meal = relationship('Meal', back_populates='ingredients')
    food = relationship('Food', back_populates='meal_ingredients')
    
    # Unique constraint to prevent duplicate ingredients in a meal
    __table_args__ = (
        UniqueConstraint('meal_id', 'food_id', name='uq_meal_food_ingredient'),
        Index('ix_meal_ingredients_meal_id', 'meal_id'),
        Index('ix_meal_ingredients_food_id', 'food_id'),
    )
    
    def __repr__(self):
        return f'<MealIngredients meal_id={self.meal_id} food_id={self.food_id}>'
