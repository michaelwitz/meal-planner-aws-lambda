"""Tests for user profile management endpoints."""

import pytest
from app.services.auth_service import AuthService
from app.models.entities import User
from app.models.database import db
from app.services import user_service


def _get_auth_headers(client, email="existing@test.com", password="password123"):
    """Helper function to get auth headers by logging in."""
    response = client.post('/api/auth/login',
                          json={
                              'login': email,
                              'password': password
                          })
    assert response.status_code == 200
    data = response.get_json()
    return {
        'Authorization': f'Bearer {data["accessToken"]}'  # Using camelCase convention
    }


def test_get_profile(client, auth_headers):
    """Test getting user profile."""
    # Make request with auth token
    response = client.get('/api/users/me', headers=auth_headers)
    
    # Check response
    assert response.status_code == 200
    data = response.get_json()
    
    # Verify response format (camelCase)
    assert 'fullName' in data
    assert 'addressLine1' in data
    assert 'stateProvinceCode' in data
    assert 'countryCode' in data
    assert 'postalCode' in data
    assert 'createdAt' in data
    assert 'updatedAt' in data
    
    # Verify data matches test user
    assert data['email'] == 'existing@test.com'
    assert data['username'] == 'existinguser'
    assert data['fullName'] == 'Existing User'
    assert data['sex'] == 'MALE'
    assert data['addressLine1'] == '123 Test St'
    assert data['city'] == 'Test City'
    assert data['stateProvinceCode'] == 'TC'
    assert data['countryCode'] == 'US'
    assert data['postalCode'] == '12345'


def test_update_and_get_profile(client, auth_headers):
    """Test updating user profile and then getting it to verify changes."""
    # Initial get to verify starting state
    response = client.get('/api/users/me', headers=auth_headers)
    assert response.status_code == 200
    initial_data = response.get_json()
    
    # Prepare update data (using camelCase as that's what the API expects)
    update_data = {
        'fullName': 'Updated Name',
        'addressLine1': '456 New Street',
        'addressLine2': 'Apt 2B',
        'city': 'New City',
        'stateProvinceCode': 'NC',
        'countryCode': 'ca',  # Test lower case gets converted to upper
        'postalCode': '67890',
        'phoneNumber': '555-9999'
    }
    
    # Update profile
    response = client.put('/api/users/me', 
                         headers=auth_headers,
                         json=update_data)
    assert response.status_code == 200
    updated_data = response.get_json()
    
    # Verify response format
    assert updated_data['fullName'] == update_data['fullName']
    assert updated_data['addressLine1'] == update_data['addressLine1']
    assert updated_data['addressLine2'] == update_data['addressLine2']
    assert updated_data['city'] == update_data['city']
    assert updated_data['stateProvinceCode'] == update_data['stateProvinceCode']
    assert updated_data['countryCode'] == 'CA'  # Should be uppercase
    assert updated_data['postalCode'] == update_data['postalCode']
    assert updated_data['phoneNumber'] == update_data['phoneNumber']
    
    # Verify email and username remained unchanged
    assert updated_data['email'] == initial_data['email']
    assert updated_data['username'] == initial_data['username']
    
    # Verify password fields are not present
    assert 'password' not in updated_data
    assert 'passwordHash' not in updated_data
    
    # Get profile again to verify persistence
    response = client.get('/api/users/me', headers=auth_headers)
    assert response.status_code == 200
    retrieved_data = response.get_json()
    
    # Verify retrieved data matches updated data
    assert retrieved_data == updated_data


def test_update_profile_partial(client, auth_headers, app):
    """Test partial profile update (only some fields)."""
    # Prepare partial update data
    update_data = {
        'fullName': 'Partially Updated Name',
        'phoneNumber': '555-8888'
    }
    
    # Make request
    response = client.put('/api/users/me', 
                         headers=auth_headers,
                         json=update_data)
    
    # Check response
    assert response.status_code == 200
    data = response.get_json()
    
    # Verify updated fields
    assert data['fullName'] == update_data['fullName']
    assert data['phoneNumber'] == update_data['phoneNumber']
    
    # Verify other fields remained unchanged
    assert data['addressLine1'] == '123 Test St'
    assert data['city'] == 'Test City'
    assert data['stateProvinceCode'] == 'TC'
    assert data['countryCode'] == 'US'
    assert data['postalCode'] == '12345'
    
    # Verify database was updated correctly
    with app.app_context():
        user = User.query.filter_by(email='existing@test.com').first()
        assert user.fullName == update_data['fullName']
        assert user.phoneNumber == update_data['phoneNumber']
        # Verify other fields remained unchanged
        assert user.addressLine1 == '123 Test St'
        assert user.city == 'Test City'
        assert user.stateProvinceCode == 'TC'
        assert user.countryCode == 'US'
        assert user.postalCode == '12345'


def test_get_profile_unauthorized(client):
    """Test getting profile without auth token fails."""
    response = client.get('/api/users/me')
    assert response.status_code == 401


def test_update_profile_unauthorized(client):
    """Test updating profile without auth token fails."""
    response = client.put('/api/users/me', json={'fullName': 'Hacker'})
    assert response.status_code == 401


def test_password_change_flow(client):
    """Test complete password change flow: login, change password, logout, login with new password."""
    email = "existing@test.com"
    old_password = "password123"
    new_password = "NewPass123"
    
    # Step 1: Login with old password
    auth_headers = _get_auth_headers(client, email, old_password)
    
    # Step 2: Change password
    new_password_data = {
        'currentPassword': old_password,
        'newPassword': new_password
    }
    response = client.put('/api/users/me/password',
                         headers=auth_headers,
                         json=new_password_data)
    assert response.status_code == 204  # No content response
    
    # Step 3: Logout (tell client to discard token)
    response = client.post('/api/auth/logout', headers=auth_headers)
    assert response.status_code == 200
    
    # Step 4: Try login with old password (should fail)
    response = client.post('/api/auth/login',
                          json={
                              'login': email,
                              'password': old_password
                          })
    assert response.status_code == 401  # Unauthorized
    
    # Step 5: Login with new password (should succeed)
    response = client.post('/api/auth/login',
                          json={
                              'login': email,
                              'password': new_password
                          })
    assert response.status_code == 200
    data = response.get_json()
    assert 'accessToken' in data
    
    # Step 6: Verify can access profile with new token
    new_auth_headers = {
        'Authorization': f'Bearer {data["accessToken"]}'
    }
    response = client.get('/api/users/me', headers=new_auth_headers)
    assert response.status_code == 200


def test_change_password_invalid_current(client, auth_headers):
    """Test changing password with incorrect current password."""
    new_password_data = {
        'currentPassword': 'wrongpassword',
        'newPassword': 'NewPass123'
    }

    response = client.put('/api/users/me/password',
                         headers=auth_headers,
                         json=new_password_data)

    assert response.status_code == 403  # Forbidden due to invalid current password


def test_change_password_unauthorized(client):
    """Test changing password without auth."""
    new_password_data = {
        'currentPassword': 'password123',
        'newPassword': 'NewPass123'
    }

    response = client.put('/api/users/me/password',
                         json=new_password_data)

    assert response.status_code == 401  # Unauthorized


def test_update_profile_validation(client, auth_headers):
    """Test profile update validation."""
    # Test invalid state code (too long)
    response = client.put('/api/users/me',
                         headers=auth_headers,
                         json={'stateProvinceCode': 'INVALID'})
    assert response.status_code == 422
    
    # Test invalid country code (too long)
    response = client.put('/api/users/me',
                         headers=auth_headers,
                         json={'countryCode': 'USA'})
    assert response.status_code == 422
    
    # Test invalid sex enum value
    response = client.put('/api/users/me',
                         headers=auth_headers,
                         json={'sex': 'INVALID'})
    assert response.status_code == 422
