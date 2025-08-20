#!/usr/bin/env python3
"""
Lambda API Test Suite
Tests all API endpoints against deployed Lambda function using seed data
"""

import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
import requests
from dataclasses import dataclass
from enum import Enum
import argparse
from pathlib import Path

# Try to import colorama for colored output (optional)
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False
    # Define dummy color constants
    class Fore:
        GREEN = RED = YELLOW = MAGENTA = CYAN = BLUE = WHITE = ''
    class Style:
        RESET_ALL = BRIGHT = ''

class TestStatus(Enum):
    """Test result status"""
    PASSED = "✅ PASSED"
    FAILED = "❌ FAILED"
    SKIPPED = "⚠️ SKIPPED"
    ERROR = "🔥 ERROR"

@dataclass
class TestResult:
    """Individual test result"""
    name: str
    endpoint: str
    method: str
    status: TestStatus
    response_time: float
    status_code: Optional[int] = None
    response_data: Optional[Dict] = None
    error_message: Optional[str] = None
    
    def __str__(self):
        if HAS_COLOR:
            color = {
                TestStatus.PASSED: Fore.GREEN,
                TestStatus.FAILED: Fore.RED,
                TestStatus.SKIPPED: Fore.YELLOW,
                TestStatus.ERROR: Fore.MAGENTA
            }.get(self.status, Fore.WHITE)
        else:
            color = ''
        
        result = f"{color}{self.status.value} {Style.RESET_ALL if HAS_COLOR else ''}{self.name}\n"
        result += f"  Endpoint: {self.method} {self.endpoint}\n"
        result += f"  Response Time: {self.response_time:.2f}s"
        
        if self.status_code:
            result += f" | Status Code: {self.status_code}"
        
        if self.error_message:
            result += f"\n  Error: {self.error_message}"
        
        return result

class LambdaAPITester:
    """Lambda API test runner"""
    
    def __init__(self, config_file: str = "config.json"):
        """
        Initialize the tester from configuration file
        
        Args:
            config_file: Path to configuration file
        """
        # Load configuration
        config_path = Path(__file__).parent / config_file
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        # Load seed data
        seed_data_path = Path(__file__).parent / self.config.get('seed_data_file', '../seed-data.json')
        if not seed_data_path.exists():
            raise FileNotFoundError(f"Seed data file not found: {seed_data_path}")
        
        with open(seed_data_path, 'r') as f:
            self.seed_data = json.load(f)
        
        # Set up API client
        self.base_url = self.config['api_gateway_url'].rstrip('/')
        self.stage = self.config['stage']
        self.timeout = self.config.get('timeout_seconds', 30)
        
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        self.results: List[TestResult] = []
        self.auth_tokens = {}  # Store auth tokens for different users
        self.current_user = None
        
    def run_test(self, name: str, method: str, endpoint: str, 
                 data: Optional[Dict] = None, 
                 expected_status: int = 200,
                 auth_user: Optional[str] = None) -> TestResult:
        """
        Run a single test
        
        Args:
            name: Test name
            method: HTTP method
            endpoint: API endpoint
            data: Request data
            expected_status: Expected status code
            auth_user: User key for authentication (admin, user1, user2)
        
        Returns:
            TestResult object
        """
        url = f"{self.base_url}/{self.stage}{endpoint}"
        headers = self.session.headers.copy()
        
        if auth_user and auth_user in self.auth_tokens:
            headers['Authorization'] = f'Bearer {self.auth_tokens[auth_user]}'
        
        start_time = time.time()
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                headers=headers,
                timeout=self.timeout
            )
            
            response_time = time.time() - start_time
            
            # Try to parse JSON response
            try:
                response_data = response.json()
            except:
                response_data = {'text': response.text}
            
            # Determine test status
            if response.status_code == expected_status:
                status = TestStatus.PASSED
                error_message = None
            else:
                status = TestStatus.FAILED
                error_message = f"Expected {expected_status}, got {response.status_code}"
                if response_data:
                    error_message += f" - {response_data}"
            
            result = TestResult(
                name=name,
                endpoint=endpoint,
                method=method,
                status=status,
                response_time=response_time,
                status_code=response.status_code,
                response_data=response_data,
                error_message=error_message
            )
            
        except requests.exceptions.Timeout:
            result = TestResult(
                name=name,
                endpoint=endpoint,
                method=method,
                status=TestStatus.ERROR,
                response_time=self.timeout,
                error_message=f"Request timeout ({self.timeout}s)"
            )
        except Exception as e:
            result = TestResult(
                name=name,
                endpoint=endpoint,
                method=method,
                status=TestStatus.ERROR,
                response_time=time.time() - start_time,
                error_message=str(e)
            )
        
        self.results.append(result)
        print(result)
        return result
    
    def test_health_check(self):
        """Test health check endpoint"""
        return self.run_test(
            name="Health Check",
            method="GET",
            endpoint="/health",
            expected_status=200
        )
    
    def test_system_info(self):
        """Test system info endpoint"""
        return self.run_test(
            name="System Info",
            method="GET",
            endpoint="/test",
            expected_status=200
        )
    
    def test_database_connection(self):
        """Test database connection"""
        return self.run_test(
            name="Database Connection",
            method="GET",
            endpoint="/test-db",
            expected_status=200
        )
    
    def test_user_login(self, user_key: str):
        """
        Test user login with seed data credentials
        
        Args:
            user_key: Key from test_credentials (admin, user1, user2)
        """
        creds = self.seed_data['test_credentials'].get(user_key)
        if not creds:
            raise ValueError(f"Unknown user key: {user_key}")
        
        result = self.run_test(
            name=f"User Login - {creds['description']}",
            method="POST",
            endpoint="/api/auth/login",
            data={
                'login': creds['email'],  # API expects 'login' not 'email'
                'password': creds['password']
            },
            expected_status=200
        )
        
        if result.status == TestStatus.PASSED and result.response_data:
            self.auth_tokens[user_key] = result.response_data.get('access_token')
        
        return result
    
    def test_invalid_login(self):
        """Test login with invalid credentials"""
        return self.run_test(
            name="Invalid Login (Should Fail)",
            method="POST",
            endpoint="/api/auth/login",
            data={
                'login': 'nonexistent@example.com',  # API expects 'login' not 'email'
                'password': 'WrongPassword123!'
            },
            expected_status=401
        )
    
    def test_profile_get(self, user_key: str):
        """Test getting user profile (requires auth)"""
        if user_key not in self.auth_tokens:
            result = TestResult(
                name=f"Get Profile - {user_key}",
                endpoint="/api/auth/profile",
                method="GET",
                status=TestStatus.SKIPPED,
                response_time=0,
                error_message=f"No auth token for {user_key}"
            )
            self.results.append(result)
            print(result)
            return result
        
        creds = self.seed_data['test_credentials'][user_key]
        return self.run_test(
            name=f"Get Profile - {creds['description']}",
            method="GET",
            endpoint="/api/auth/profile",
            auth_user=user_key,
            expected_status=200
        )
    
    def test_profile_update(self, user_key: str):
        """Test updating user profile (requires auth)"""
        if user_key not in self.auth_tokens:
            result = TestResult(
                name=f"Update Profile - {user_key}",
                endpoint="/api/auth/profile",
                method="PUT",
                status=TestStatus.SKIPPED,
                response_time=0,
                error_message=f"No auth token for {user_key}"
            )
            self.results.append(result)
            print(result)
            return result
        
        creds = self.seed_data['test_credentials'][user_key]
        # Just update the full name
        return self.run_test(
            name=f"Update Profile - {creds['description']}",
            method="PUT",
            endpoint="/api/auth/profile",
            data={
                'full_name': f"Updated {creds['email'].split('@')[0]}"
            },
            auth_user=user_key,
            expected_status=200
        )
    
    def test_refresh_token(self, user_key: str):
        """Test token refresh"""
        if user_key not in self.auth_tokens:
            result = TestResult(
                name=f"Refresh Token - {user_key}",
                endpoint="/api/auth/refresh",
                method="POST",
                status=TestStatus.SKIPPED,
                response_time=0,
                error_message=f"No auth token for {user_key}"
            )
            self.results.append(result)
            print(result)
            return result
        
        creds = self.seed_data['test_credentials'][user_key]
        return self.run_test(
            name=f"Refresh Token - {creds['description']}",
            method="POST",
            endpoint="/api/auth/refresh",
            auth_user=user_key,
            expected_status=200
        )
    
    def test_logout(self, user_key: str):
        """Test user logout"""
        if user_key not in self.auth_tokens:
            result = TestResult(
                name=f"Logout - {user_key}",
                endpoint="/api/auth/logout",
                method="POST",
                status=TestStatus.SKIPPED,
                response_time=0,
                error_message=f"No auth token for {user_key}"
            )
            self.results.append(result)
            print(result)
            return result
        
        creds = self.seed_data['test_credentials'][user_key]
        return self.run_test(
            name=f"Logout - {creds['description']}",
            method="POST",
            endpoint="/api/auth/logout",
            auth_user=user_key,
            expected_status=200
        )
    
    def test_unauthorized_access(self):
        """Test accessing protected endpoint without auth"""
        return self.run_test(
            name="Unauthorized Access (Should Fail)",
            method="GET",
            endpoint="/api/auth/profile",
            expected_status=401
        )
    
    def test_missing_fields(self):
        """Test login with missing required fields"""
        return self.run_test(
            name="Missing Password Field (Should Fail)",
            method="POST",
            endpoint="/api/auth/login",
            data={'login': 'incomplete@example.com'},  # Missing password
            expected_status=422  # Pydantic validation error
        )
    
    def test_new_user_registration(self):
        """Test registering a new user (not in seed data)"""
        timestamp = int(time.time())
        new_user = {
            'email': f'newuser_{timestamp}@example.com',
            'username': f'newuser_{timestamp}',
            'password': 'NewPassword123!',
            'full_name': 'New Test User',
            'sex': 'OTHER',  # Required field
            'phone_number': '555-0000',  # Optional but let's include it
            'address_line_1': '123 Test Street',  # Required
            'address_line_2': 'Apt 4B',  # Optional
            'city': 'Test City',  # Required
            'state_province_code': 'TC',  # Required
            'country_code': 'US',  # Required
            'postal_code': '12345'  # Required
        }
        
        result = self.run_test(
            name="New User Registration",
            method="POST",
            endpoint="/api/auth/register",
            data=new_user,
            expected_status=201
        )
        
        # If registration successful, try to login
        if result.status == TestStatus.PASSED:
            login_result = self.run_test(
                name="New User Login",
                method="POST",
                endpoint="/api/auth/login",
                data={
                    'login': new_user['email'],  # API expects 'login' not 'email'
                    'password': new_user['password']
                },
                expected_status=200
            )
            
            if login_result.status == TestStatus.PASSED and login_result.response_data:
                self.auth_tokens['new_user'] = login_result.response_data.get('access_token')
        
        return result
    
    def test_duplicate_registration(self):
        """Test duplicate user registration (should fail)"""
        # Try to register an existing user from seed data
        existing_user = self.seed_data['users'][0]  # Admin user
        return self.run_test(
            name="Duplicate Registration (Should Fail)",
            method="POST",
            endpoint="/api/auth/register",
            data={
                'email': existing_user['email'],
                'username': 'different_username',  # Different username but same email
                'password': 'SomePassword123!',
                'full_name': existing_user['full_name'],
                'sex': existing_user.get('sex', 'OTHER'),
                'address_line_1': existing_user['address_line_1'],
                'city': existing_user['city'],
                'state_province_code': existing_user['state_province_code'],
                'country_code': existing_user['country_code'],
                'postal_code': existing_user['postal_code']
            },
            expected_status=400  # Should get 400 for duplicate email
        )
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        print(f"\n{'='*60}")
        print(f"Lambda API Test Suite")
        print(f"Target: {self.base_url}/{self.stage}")
        print(f"Config: {Path(__file__).parent / 'config.json'}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")
        
        # Infrastructure tests
        print(f"\n--- Infrastructure Tests ---")
        self.test_health_check()
        self.test_system_info()
        self.test_database_connection()
        
        # Authentication tests with seed data users
        print(f"\n--- Authentication Tests (Seed Data Users) ---")
        for user_key in ['admin', 'user1', 'user2']:
            self.test_user_login(user_key)
        
        self.test_invalid_login()
        
        # Protected endpoint tests
        print(f"\n--- Protected Endpoint Tests ---")
        for user_key in ['admin', 'user1']:
            self.test_profile_get(user_key)
            self.test_profile_update(user_key)
            self.test_refresh_token(user_key)
        
        self.test_unauthorized_access()
        
        # Registration tests
        print(f"\n--- Registration Tests ---")
        self.test_new_user_registration()
        self.test_duplicate_registration()
        
        # Validation tests
        print(f"\n--- Validation Tests ---")
        self.test_missing_fields()
        
        # Cleanup
        print(f"\n--- Cleanup ---")
        for user_key in ['admin', 'user1']:
            self.test_logout(user_key)
        
        # Print summary
        return self.print_summary()
    
    def print_summary(self):
        """Print test summary and return exit code"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in self.results if r.status == TestStatus.FAILED)
        skipped = sum(1 for r in self.results if r.status == TestStatus.SKIPPED)
        errors = sum(1 for r in self.results if r.status == TestStatus.ERROR)
        
        avg_response_time = sum(r.response_time for r in self.results) / total if total > 0 else 0
        
        print(f"\n{'='*60}")
        print(f"Test Summary")
        print(f"{'='*60}")
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Skipped: {skipped}")
        print(f"Errors: {errors}")
        print(f"Average Response Time: {avg_response_time:.2f}s")
        
        if failed > 0 or errors > 0:
            print(f"\nFailed/Error Tests:")
            for result in self.results:
                if result.status in [TestStatus.FAILED, TestStatus.ERROR]:
                    print(f"  - {result.name}: {result.error_message}")
        
        # Overall result
        if failed == 0 and errors == 0:
            print(f"\n✅ All tests passed successfully!")
        else:
            print(f"\n❌ Some tests failed. Please review the results above.")
        
        print(f"{'='*60}\n")
        
        # Return exit code
        return 0 if (failed == 0 and errors == 0) else 1

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Test Lambda API endpoints using seed data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_lambda_api.py                    # Run all tests
  python test_lambda_api.py --config prod.json # Use different config
  python test_lambda_api.py --test health      # Run specific test
  python test_lambda_api.py --user admin       # Test specific user
        """
    )
    
    parser.add_argument(
        '--config',
        default='config.json',
        help='Configuration file (default: config.json)'
    )
    
    parser.add_argument(
        '--test',
        help='Run specific test only',
        choices=[
            'health', 'system', 'database', 'login', 'register',
            'profile', 'refresh', 'logout', 'all'
        ],
        default='all'
    )
    
    parser.add_argument(
        '--user',
        help='Test specific user only',
        choices=['admin', 'user1', 'user2', 'all'],
        default='all'
    )
    
    args = parser.parse_args()
    
    try:
        # Create tester
        tester = LambdaAPITester(args.config)
        
        # Run tests based on selection
        if args.test == 'all':
            exit_code = tester.run_all_tests()
        else:
            # Run specific test
            test_map = {
                'health': tester.test_health_check,
                'system': tester.test_system_info,
                'database': tester.test_database_connection,
                'login': lambda: tester.test_user_login(args.user if args.user != 'all' else 'admin'),
                'register': tester.test_new_user_registration,
                'profile': lambda: tester.test_profile_get(args.user if args.user != 'all' else 'admin'),
                'refresh': lambda: tester.test_refresh_token(args.user if args.user != 'all' else 'admin'),
                'logout': lambda: tester.test_logout(args.user if args.user != 'all' else 'admin'),
            }
            
            test_func = test_map.get(args.test)
            if test_func:
                # If testing auth endpoints, login first if needed
                if args.test in ['profile', 'refresh', 'logout']:
                    user_key = args.user if args.user != 'all' else 'admin'
                    tester.test_user_login(user_key)
                
                test_func()
                exit_code = tester.print_summary()
            else:
                print(f"Unknown test: {args.test}")
                exit_code = 1
                
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print(f"Make sure config.json and seed-data.json exist")
        exit_code = 1
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        exit_code = 1
    
    sys.exit(exit_code)

if __name__ == '__main__':
    main()
