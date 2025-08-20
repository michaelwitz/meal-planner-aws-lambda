# Testing Documentation

This document describes the testing structure and setup for the Meal Planner API.

## Test Structure

The project has three main test files:
1. `tests/test_auth.py` - Authentication tests
2. `tests/test_users.py` - User-related tests
3. `tests/api/test_lambda_api.py` - Lambda API integration tests

### Test Configuration (conftest.py)

The `conftest.py` file provides key pytest fixtures:
- `app`: Creates a Flask test app with a clean database for each test
- `client`: Flask test client for making HTTP requests
- `auth_headers`: Provides authentication headers with a valid JWT token
- Creates a test user (`existing@test.com`/`password123`) for auth tests

```python
@pytest.fixture(scope='function')
def app():
    app = create_app('development-local')
    with app.app_context():
        db.create_all()
        # Add test user
```

## Local Tests

### Authentication Tests (test_auth.py)
Tests all authentication endpoints:
- User registration
- Login (with email or username)
- Profile retrieval
- Logout
- Various validation cases (duplicate emails, invalid passwords, etc.)

### User Profile Tests (test_users.py)
Tests user profile management:
- Getting user profile
- Updating profile (full and partial updates)
- Password change flow
- Authorization checks
- Input validation

## Lambda API Tests (test_lambda_api.py)

The Lambda API tests are designed to test your API endpoints when deployed to AWS Lambda. This is different from local tests as it:
1. Tests against the deployed Lambda function
2. Uses seed data for testing
3. Tests the full integration with API Gateway

### Lambda Test Structure

1. Infrastructure Tests:
   - Health check
   - System info
   - Database connection

2. Authentication Tests:
   - User login with seed data
   - Invalid login attempts
   - Profile retrieval and updates
   - Token refresh
   - Logout

3. Registration Tests:
   - New user registration
   - Duplicate registration handling

4. Validation Tests:
   - Missing fields
   - Invalid data

## How Tests Work

When pytest runs with a payload, here's what happens:

1. **Setup**: The conftest.py creates a fresh test database and Flask client:
```python
@pytest.fixture(scope='function')
def app():
    app = create_app('development-local')
    with app.app_context():
        db.create_all()
        # Add test user
```

2. **Request Simulation**: The test client simulates HTTP requests:
```python
response = client.post('/api/auth/register', 
                      json=new_user_data,
                      content_type='application/json')
```

3. **Response Validation**: Tests check both status codes and response data:
```python
assert response.status_code == 201
data = response.get_json()
assert 'accessToken' in data
assert data['user']['email'] == 'newuser@test.com'
```

4. **Cleanup**: After each test, the database is cleaned up:
```python
# In conftest.py
yield app
with app.app_context():
    db.session.remove()
    db.drop_all()
```

## Running Tests

### Local Tests

1. Run all tests:
```bash
pytest
```

2. Run specific test files or functions:
```bash
pytest tests/test_auth.py  # Run all auth tests
pytest tests/test_auth.py::TestAuthentication::test_login_with_email_success  # Run specific test
```

### Lambda API Tests

```bash
python tests/api/test_lambda_api.py  # Run all Lambda API tests
python tests/api/test_lambda_api.py --test login  # Run specific test
```

## What's Being Tested

The test suite ensures that:
1. Your API endpoints work correctly
2. Authentication and authorization work
3. Data validation is working
4. Error handling is appropriate
5. The deployed Lambda function is working correctly
