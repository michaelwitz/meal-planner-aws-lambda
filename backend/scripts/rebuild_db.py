#!/usr/bin/env python3
"""
Development script to drop, recreate, and seed the database.
Usage: 
    python scripts/rebuild_db.py           # Use default database
    python scripts/rebuild_db.py --local   # Use local test database
    python scripts/rebuild_db.py --cloud   # Use cloud test database
"""

import sys
import os
import argparse
from datetime import datetime, date, timedelta

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def drop_all_tables():
    """Drop all database tables with CASCADE to handle foreign keys."""
    print("Dropping all tables...")
    
    # Get all table names from metadata
    tables = db.metadata.tables.keys()
    
    if tables:
        # Use raw SQL with CASCADE to drop all constraints and tables
        with db.engine.connect() as conn:
            # First, drop all tables with CASCADE (PostgreSQL specific)
            # This will automatically handle foreign key constraints
            for table in reversed(list(tables)):
                try:
                    conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
                    conn.commit()
                    print(f"  ✓ Dropped table {table}")
                except Exception as e:
                    print(f"  ✗ Error dropping table {table}: {e}")
                    conn.rollback()
    
    print("✓ All tables dropped")


def create_all_tables():
    """Create all database tables."""
    print("Creating all tables...")
    db.create_all()
    print("✓ All tables created")


def hash_password(password):
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def seed_users():
    """Seed user data."""
    print("Seeding users...")
    
    users = [
        User(
            email='admin@mealplanner.com',
            username='admin',
            password_hash=hash_password('admin123'),
            full_name='Admin User',
            sex=SexEnum.OTHER.value,
            phone_number='555-0100',
            address_line_1='123 Admin St',
            city='San Francisco',
            state_province_code='CA',
            country_code='US',
            postal_code='94102',
            created_at=datetime.utcnow()
        ),
        User(
            email='john.doe@example.com',
            username='johndoe',
            password_hash=hash_password('password123'),
            full_name='John Doe',
            sex=SexEnum.MALE.value,
            phone_number='555-0101',
            address_line_1='456 Oak Ave',
            address_line_2='Apt 2B',
            city='New York',
            state_province_code='NY',
            country_code='US',
            postal_code='10001',
            created_at=datetime.utcnow()
        ),
        User(
            email='jane.smith@example.com',
            username='janesmith',
            password_hash=hash_password('password123'),
            full_name='Jane Smith',
            sex=SexEnum.FEMALE.value,
            phone_number='555-0102',
            address_line_1='789 Pine Rd',
            city='Austin',
            state_province_code='TX',
            country_code='US',
            postal_code='78701',
            created_at=datetime.utcnow()
        )
    ]
    
    for user in users:
        db.session.add(user)
    
    db.session.commit()
    print(f"✓ Seeded {len(users)} users")
    return users


def seed_foods():
    """Seed food catalog data."""
    print("Seeding food catalog...")
    
    foods = [
        # MEAT
        Food(
            name='Grilled Chicken Breast',
            category=FoodCategoryEnum.MEAT.value,
            calories=165,
            protein=31.0,
            carbs=0,
            fat=3.6,
            fiber=0,
            serving_size='100',
            unit='grams',
            non_inflammatory=True,
            created_at=datetime.utcnow()
        ),
        Food(
            name='Lean Ground Beef',
            category=FoodCategoryEnum.MEAT.value,
            calories=250,
            protein=26.0,
            carbs=0,
            fat=17.0,
            fiber=0,
            serving_size='100',
            unit='grams',
            non_inflammatory=False,
            created_at=datetime.utcnow()
        ),
        
        # FISH
        Food(
            name='Salmon Fillet',
            category=FoodCategoryEnum.FISH.value,
            calories=208,
            protein=20.0,
            carbs=0,
            fat=13.0,
            fiber=0,
            serving_size='100',
            unit='grams',
            non_inflammatory=True,
            created_at=datetime.utcnow()
        ),
        Food(
            name='Tuna Steak',
            category=FoodCategoryEnum.FISH.value,
            calories=132,
            protein=28.0,
            carbs=0,
            fat=1.3,
            fiber=0,
            serving_size='100',
            unit='grams',
            non_inflammatory=True,
            created_at=datetime.utcnow()
        ),
        
        # GRAINS
        Food(
            name='Brown Rice',
            category=FoodCategoryEnum.GRAIN.value,
            calories=112,
            protein=2.6,
            carbs=23.5,
            fat=0.9,
            fiber=1.8,
            serving_size='100',
            unit='grams',
            non_inflammatory=True,
            created_at=datetime.utcnow()
        ),
        Food(
            name='Quinoa',
            category=FoodCategoryEnum.GRAIN.value,
            calories=120,
            protein=4.1,
            carbs=21.3,
            fat=1.9,
            fiber=2.8,
            serving_size='100',
            unit='grams',
            non_inflammatory=True,
            created_at=datetime.utcnow()
        ),
        
        # VEGETABLES
        Food(
            name='Broccoli',
            category=FoodCategoryEnum.VEGETABLE.value,
            calories=34,
            protein=2.8,
            carbs=7.0,
            fat=0.4,
            fiber=2.6,
            serving_size='100',
            unit='grams',
            non_inflammatory=True,
            created_at=datetime.utcnow()
        ),
        Food(
            name='Spinach',
            category=FoodCategoryEnum.VEGETABLE.value,
            calories=23,
            protein=2.9,
            carbs=3.6,
            fat=0.4,
            fiber=2.2,
            serving_size='100',
            unit='grams',
            non_inflammatory=True,
            created_at=datetime.utcnow()
        ),
        
        # NIGHTSHADES
        Food(
            name='Tomato',
            category=FoodCategoryEnum.NIGHTSHADES.value,
            calories=18,
            protein=0.9,
            carbs=3.9,
            fat=0.2,
            fiber=1.2,
            serving_size='100',
            unit='grams',
            non_inflammatory=False,
            created_at=datetime.utcnow()
        ),
        Food(
            name='Bell Pepper',
            category=FoodCategoryEnum.NIGHTSHADES.value,
            calories=31,
            protein=1.0,
            carbs=6.0,
            fat=0.3,
            fiber=2.1,
            serving_size='100',
            unit='grams',
            non_inflammatory=False,
            created_at=datetime.utcnow()
        ),
        
        # FRUITS
        Food(
            name='Apple',
            category=FoodCategoryEnum.FRUIT.value,
            calories=52,
            protein=0.3,
            carbs=14.0,
            fat=0.2,
            fiber=2.4,
            serving_size='1 medium',
            unit='piece',
            non_inflammatory=True,
            created_at=datetime.utcnow()
        ),
        Food(
            name='Banana',
            category=FoodCategoryEnum.FRUIT.value,
            calories=89,
            protein=1.1,
            carbs=23.0,
            fat=0.3,
            fiber=2.6,
            serving_size='1 medium',
            unit='piece',
            non_inflammatory=True,
            created_at=datetime.utcnow()
        ),
        
        # DAIRY
        Food(
            name='Greek Yogurt',
            category=FoodCategoryEnum.DAIRY.value,
            calories=59,
            protein=10.0,
            carbs=3.6,
            fat=0.4,
            fiber=0,
            serving_size='100',
            unit='grams',
            non_inflammatory=False,
            created_at=datetime.utcnow()
        ),
        
        # OIL
        Food(
            name='Olive Oil',
            category=FoodCategoryEnum.OIL.value,
            calories=884,
            protein=0,
            carbs=0,
            fat=100.0,
            fiber=0,
            serving_size='100',
            unit='ml',
            non_inflammatory=True,
            created_at=datetime.utcnow()
        ),
        
        # SPICE_HERB
        Food(
            name='Turmeric',
            category=FoodCategoryEnum.SPICE_HERB.value,
            calories=312,
            protein=9.7,
            carbs=67.1,
            fat=3.3,
            fiber=22.7,
            serving_size='100',
            unit='grams',
            non_inflammatory=True,
            created_at=datetime.utcnow()
        ),
        
        # SWEETENER
        Food(
            name='Honey',
            category=FoodCategoryEnum.SWEETENER.value,
            calories=304,
            protein=0.3,
            carbs=82.4,
            fat=0,
            fiber=0.2,
            serving_size='100',
            unit='grams',
            non_inflammatory=True,
            created_at=datetime.utcnow()
        )
    ]
    
    for food in foods:
        db.session.add(food)
    
    db.session.commit()
    print(f"✓ Seeded {len(foods)} food items")
    return foods


def seed_meals(foods):
    """Seed meal data."""
    print("Seeding meals...")
    
    # Create some meals
    meals = [
        Meal(
            name='Healthy Chicken Bowl',
            description='Grilled chicken with brown rice and vegetables',
            total_calories=350,
            total_protein=40,
            total_carbs=35,
            total_fat=8,
            prep_time=25,
            created_at=datetime.utcnow()
        ),
        Meal(
            name='Salmon Power Plate',
            description='Baked salmon with quinoa and spinach',
            total_calories=380,
            total_protein=32,
            total_carbs=28,
            total_fat=15,
            prep_time=30,
            created_at=datetime.utcnow()
        ),
        Meal(
            name='Morning Energy Bowl',
            description='Greek yogurt with banana and honey',
            total_calories=250,
            total_protein=12,
            total_carbs=45,
            total_fat=2,
            prep_time=5,
            created_at=datetime.utcnow()
        )
    ]
    
    for meal in meals:
        db.session.add(meal)
    
    db.session.commit()
    print(f"✓ Seeded {len(meals)} meals")
    return meals


def seed_meal_ingredients(meals, foods):
    """Seed meal ingredients."""
    print("Seeding meal ingredients...")
    
    # Find foods by name for easier reference
    food_dict = {food.name: food for food in foods}
    
    ingredients = [
        # Healthy Chicken Bowl
        MealIngredients(
            meal_id=meals[0].id,
            food_id=food_dict['Grilled Chicken Breast'].id,
            quantity=150,
            unit='grams',
            notes='Seasoned with herbs',
            created_at=datetime.utcnow()
        ),
        MealIngredients(
            meal_id=meals[0].id,
            food_id=food_dict['Brown Rice'].id,
            quantity=100,
            unit='grams',
            created_at=datetime.utcnow()
        ),
        MealIngredients(
            meal_id=meals[0].id,
            food_id=food_dict['Broccoli'].id,
            quantity=100,
            unit='grams',
            created_at=datetime.utcnow()
        ),
        
        # Salmon Power Plate
        MealIngredients(
            meal_id=meals[1].id,
            food_id=food_dict['Salmon Fillet'].id,
            quantity=120,
            unit='grams',
            created_at=datetime.utcnow()
        ),
        MealIngredients(
            meal_id=meals[1].id,
            food_id=food_dict['Quinoa'].id,
            quantity=100,
            unit='grams',
            created_at=datetime.utcnow()
        ),
        MealIngredients(
            meal_id=meals[1].id,
            food_id=food_dict['Spinach'].id,
            quantity=150,
            unit='grams',
            created_at=datetime.utcnow()
        ),
        
        # Morning Energy Bowl
        MealIngredients(
            meal_id=meals[2].id,
            food_id=food_dict['Greek Yogurt'].id,
            quantity=200,
            unit='grams',
            created_at=datetime.utcnow()
        ),
        MealIngredients(
            meal_id=meals[2].id,
            food_id=food_dict['Banana'].id,
            quantity=1,
            unit='piece',
            created_at=datetime.utcnow()
        ),
        MealIngredients(
            meal_id=meals[2].id,
            food_id=food_dict['Honey'].id,
            quantity=20,
            unit='grams',
            created_at=datetime.utcnow()
        )
    ]
    
    for ingredient in ingredients:
        db.session.add(ingredient)
    
    db.session.commit()
    print(f"✓ Seeded {len(ingredients)} meal ingredients")


def seed_user_favorites(users, foods):
    """Seed user favorite foods."""
    print("Seeding user favorite foods...")
    
    # Find foods by name
    food_dict = {food.name: food for food in foods}
    
    favorites = [
        # Admin likes healthy options
        FoodUserLikes(
            user_id=users[0].id,
            food_id=food_dict['Salmon Fillet'].id,
            created_at=datetime.utcnow()
        ),
        FoodUserLikes(
            user_id=users[0].id,
            food_id=food_dict['Quinoa'].id,
            created_at=datetime.utcnow()
        ),
        FoodUserLikes(
            user_id=users[0].id,
            food_id=food_dict['Broccoli'].id,
            created_at=datetime.utcnow()
        ),
        
        # John likes meat and grains
        FoodUserLikes(
            user_id=users[1].id,
            food_id=food_dict['Grilled Chicken Breast'].id,
            created_at=datetime.utcnow()
        ),
        FoodUserLikes(
            user_id=users[1].id,
            food_id=food_dict['Brown Rice'].id,
            created_at=datetime.utcnow()
        ),
        
        # Jane likes fruits and dairy
        FoodUserLikes(
            user_id=users[2].id,
            food_id=food_dict['Greek Yogurt'].id,
            created_at=datetime.utcnow()
        ),
        FoodUserLikes(
            user_id=users[2].id,
            food_id=food_dict['Banana'].id,
            created_at=datetime.utcnow()
        ),
        FoodUserLikes(
            user_id=users[2].id,
            food_id=food_dict['Apple'].id,
            created_at=datetime.utcnow()
        )
    ]
    
    for favorite in favorites:
        db.session.add(favorite)
    
    db.session.commit()
    print(f"✓ Seeded {len(favorites)} user favorite foods")


def seed_user_meals(users, meals):
    """Seed user meals with dates."""
    print("Seeding user meals...")
    
    today = date.today()
    
    user_meals = [
        # Admin's meals for the week
        UserMeal(
            user_id=users[0].id,
            meal_id=meals[0].id,  # Chicken Bowl
            date=today,
            meal_number=2,  # Lunch
            created_at=datetime.utcnow()
        ),
        UserMeal(
            user_id=users[0].id,
            meal_id=meals[1].id,  # Salmon Plate
            date=today,
            meal_number=3,  # Dinner
            created_at=datetime.utcnow()
        ),
        UserMeal(
            user_id=users[0].id,
            meal_id=meals[2].id,  # Energy Bowl
            date=today + timedelta(days=1),
            meal_number=1,  # Breakfast
            created_at=datetime.utcnow()
        ),
        
        # John's meals
        UserMeal(
            user_id=users[1].id,
            meal_id=meals[0].id,  # Chicken Bowl
            date=today,
            meal_number=2,  # Lunch
            created_at=datetime.utcnow()
        ),
        UserMeal(
            user_id=users[1].id,
            meal_id=meals[0].id,  # Chicken Bowl again
            date=today + timedelta(days=1),
            meal_number=3,  # Dinner
            created_at=datetime.utcnow()
        ),
        
        # Jane's meals
        UserMeal(
            user_id=users[2].id,
            meal_id=meals[2].id,  # Energy Bowl
            date=today,
            meal_number=1,  # Breakfast
            created_at=datetime.utcnow()
        ),
        UserMeal(
            user_id=users[2].id,
            meal_id=meals[1].id,  # Salmon Plate
            date=today,
            meal_number=3,  # Dinner
            created_at=datetime.utcnow()
        )
    ]
    
    for user_meal in user_meals:
        db.session.add(user_meal)
    
    db.session.commit()
    print(f"✓ Seeded {len(user_meals)} user meals")


def rebuild_database(target=None):
    """Main function to rebuild the database.
    
    Args:
        target: Database target ('local', 'cloud', or None for default)
    """
    print("\n" + "="*50)
    print("DATABASE REBUILD SCRIPT")
    print("="*50 + "\n")
    
    # If target specified, import and use test database configuration
    if target in ['local', 'cloud']:
        from tests.db_config import TestDatabaseConfig
        database_url = TestDatabaseConfig.get_database_url(target)
        os.environ['DATABASE_URL'] = database_url
        print(f"Using {target} database: {TestDatabaseConfig.get_config(target).description}")
        db_info = f"Database: {target} test database"
    else:
        # Determine which database based on USE_LOCAL_DB
        use_local = os.environ.get('USE_LOCAL_DB', 'true').lower() == 'true'
        if use_local:
            db_info = "Database: local development database (port 5455)"
        else:
            db_info = "Database: cloud RDS Serverless database"
    
    # Import app modules after setting DATABASE_URL
    from app import create_app
    from app.models.database import db
    from app.models.entities import (
        User, Food, Meal, FoodUserLikes, UserMeal, MealIngredients,
        SexEnum, FoodCategoryEnum
    )
    import bcrypt
    from sqlalchemy import text
    
    # Make these available globally for the seed functions
    globals()['db'] = db
    globals()['User'] = User
    globals()['Food'] = Food
    globals()['Meal'] = Meal
    globals()['FoodUserLikes'] = FoodUserLikes
    globals()['UserMeal'] = UserMeal
    globals()['MealIngredients'] = MealIngredients
    globals()['SexEnum'] = SexEnum
    globals()['FoodCategoryEnum'] = FoodCategoryEnum
    globals()['bcrypt'] = bcrypt
    globals()['text'] = text
    
    # Determine config based on USE_LOCAL_DB environment variable
    use_local = os.environ.get('USE_LOCAL_DB', 'true').lower() == 'true'
    config_name = 'development-local' if use_local else 'development-cloud'
    app = create_app(config_name)
    
    with app.app_context():
        try:
            # Drop all tables (CASCADE handles foreign keys)
            drop_all_tables()
            
            # Create all tables
            create_all_tables()
            
            # Seed data in order (respecting foreign key dependencies)
            users = seed_users()
            foods = seed_foods()
            meals = seed_meals(foods)
            seed_meal_ingredients(meals, foods)
            seed_user_favorites(users, foods)
            seed_user_meals(users, meals)
            
            print("\n" + "="*50)
            print("✓ DATABASE REBUILD COMPLETE!")
            print("="*50)
            print("\nTest credentials:")
            print("  Admin: admin@mealplanner.com / admin123")
            print("  User1: john.doe@example.com / password123")
            print("  User2: jane.smith@example.com / password123")
            print(f"\n{db_info}")
            print("\n")
            
        except Exception as e:
            print(f"\n✗ Error rebuilding database: {e}")
            db.session.rollback()
            import traceback
            traceback.print_exc()
            sys.exit(1)


def main():
    """Parse arguments and run rebuild."""
    parser = argparse.ArgumentParser(
        description='Rebuild database with fresh schema and seed data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/rebuild_db.py           # Use default development database
  python scripts/rebuild_db.py --local   # Use local test database
  python scripts/rebuild_db.py --cloud   # Use cloud test database
        """
    )
    
    # Database selection
    db_group = parser.add_mutually_exclusive_group()
    db_group.add_argument(
        '--local',
        action='store_true',
        help='Use local test database'
    )
    db_group.add_argument(
        '--cloud',
        action='store_true',
        help='Use cloud test database'
    )
    
    args = parser.parse_args()
    
    # Determine target
    target = None
    if args.local:
        target = 'local'
    elif args.cloud:
        target = 'cloud'
    
    rebuild_database(target)


if __name__ == '__main__':
    main()
