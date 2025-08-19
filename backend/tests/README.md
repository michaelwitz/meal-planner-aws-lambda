# Meal Planner API Tests

## Overview
This directory contains all unit and integration tests for the Meal Planner API.
Tests are run against a local Docker PostgreSQL database.

## Test Structure
- `conftest.py` - Pytest fixtures and test configuration
- `db_config.py` - Database configuration for local testing
- `run_tests.py` - Convenient test runner script
- `test_auth.py` - Authentication endpoint tests

## Database Configuration

### Environment Variables
All database URLs are configured in the `.env` file in the project root.

#### Development Database
- `DEV_DATABASE_URL` - Development database connection (port 5455)
- Used when running the Flask app locally with `flask run`

#### Test Database
- `TEST_DATABASE_URL_LOCAL` - Local Docker test database (port 5456)
- `TEST_DATABASE_URL` - Active test database (automatically set by test runner)

**Note:** The test runner script (`run_tests.py`) automatically sets `TEST_DATABASE_URL` to use the local test database.

## Using the Test Runner Script

The `run_tests.py` script provides a convenient way to run tests:

```bash
# From the backend directory
python tests/run_tests.py                    # Run all tests
python tests/run_tests.py --check            # Check database connection
python tests/run_tests.py --verbose          # Run with verbose output
python tests/run_tests.py --coverage         # Run with coverage report
python tests/run_tests.py --file tests/test_auth.py  # Run specific test file
```

## Running Tests with Local Database

### Prerequisites
1. Activate the Python environment:
   ```bash
   conda activate meal-planner
   ```

2. Start the local test database:
   ```bash
   # From project root
   docker-compose -f docker-compose.test.yml up -d
   ```

### Run Tests
```bash
# Using the test runner script (recommended)
python tests/run_tests.py

# Or directly with pytest (requires TEST_DATABASE_URL to be set)
pytest

# With verbose output
python tests/run_tests.py --verbose

# With coverage report
python tests/run_tests.py --coverage
```


### Run Specific Test Files
```bash
# Run only authentication tests
pytest tests/test_auth.py -v
```

### Run Specific Test Cases
```bash
# Run a specific test class
pytest tests/test_auth.py::TestAuthentication -v

# Run a specific test method
pytest tests/test_auth.py::TestAuthentication::test_register_new_user_success -v
```

## Test Coverage

### Check Coverage for Specific Modules
```bash
# Coverage for auth module
pytest tests/test_auth.py --cov=app.blueprints.auth --cov=app.services.auth_service --cov-report=term-missing
```

### Generate HTML Coverage Report
```bash
pytest --cov=app --cov-report=html
# Open htmlcov/index.html in browser
```

## Test Database

### Local Test Database (Docker)
- **Port**: 5456 (different from development port 5455)
- **Container**: `meal_planner_test_db`
- **Database**: `meal_planner_test_db`
- **Docker Compose**: `docker-compose.test.yml`

**Note**: The database is automatically cleared and recreated for each test function to ensure test isolation.

## Writing New Tests

### Test Structure
```python
class TestFeatureName:
    """Group related tests in a class."""
    
    def test_successful_case(self, client):
        """Test the happy path."""
        # Arrange: Set up test data
        # Act: Perform the action
        # Assert: Check the results
        
    def test_error_case(self, client):
        """Test error handling."""
        # Test validation errors, edge cases, etc.
```

### Available Fixtures
- `app` - Flask application configured for testing
- `client` - Test client for making HTTP requests
- `auth_headers` - Headers with valid JWT token for authenticated requests
- `runner` - CLI runner for testing Flask commands

## Cleanup
After running tests, stop the test database:
```bash
docker-compose -f docker-compose.test.yml down
```

## Current Test Status
✅ **Authentication Tests (16/16 passing)**
- User registration with validation
- Duplicate email/username prevention  
- Password strength validation
- Missing required fields validation
- Invalid email format validation
- Invalid sex value validation
- Login with email or username
- Empty credentials handling
- Invalid credential handling
- JWT-protected profile endpoint
- Invalid/missing token handling
- Logout functionality

## TODO
- [ ] Add tests for password reset endpoints (when implemented)
- [ ] Add tests for token refresh endpoints (when implemented)
- [ ] Add tests for user profile update endpoints
- [ ] Add tests for food catalog endpoints
- [ ] Add tests for meal planning endpoints
- [ ] Add tests for user favorites endpoints
