#!/usr/bin/env python3
"""
Test runner script for Meal Planner API.

This script provides an easy way to run tests against the local Docker database.

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py --check            # Check database connection
    python run_tests.py --verbose          # Run in verbose mode
    python run_tests.py --file tests/test_auth.py  # Run specific test file
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path

# Add backend directory to path to import test modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.db_config import TestDatabaseConfig


def check_database_connection():
    """Check connection to the local test database."""
    print("🔍 Checking database connection...\n")
    
    print("Local Test Database:")
    try:
        TestDatabaseConfig.validate_connection()
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        print("   💡 Tip: Make sure Docker is running and start the test database:")
        print("      docker-compose -f docker-compose.test.yml up -d\n")


def run_tests(args):
    """Run pytest with the specified configuration."""
    import os
    from dotenv import load_dotenv
    from pathlib import Path
    
    # Load .env file
    project_root = Path(__file__).parent.parent.parent
    env_path = project_root / '.env'
    load_dotenv(env_path)
    
    # Set TEST_DATABASE_URL to local database
    local_url = os.getenv('TEST_DATABASE_URL_LOCAL')
    if not local_url:
        print("❌ TEST_DATABASE_URL_LOCAL not found in .env file")
        return 1
    os.environ['TEST_DATABASE_URL'] = local_url
    print("🏠 Running tests with LOCAL database")
    print(f"   Database: Docker PostgreSQL on port 5456")
    
    # Build pytest command
    pytest_args = ['pytest']
    
    # Add verbose flag
    if args.verbose:
        pytest_args.append('-v')
    
    # Add coverage report
    if args.coverage:
        pytest_args.extend(['--cov=app', '--cov-report=term-missing'])
    
    # Add specific test file or directory
    if args.file:
        pytest_args.append(args.file)
    
    # Add any additional pytest arguments
    if args.pytest_args:
        pytest_args.extend(args.pytest_args)
    
    print(f"📝 Command: {' '.join(pytest_args)}\n")
    
    # Run pytest
    result = subprocess.run(pytest_args)
    return result.returncode


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Run Meal Planner API tests with local Docker database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                     # Run all tests
  python run_tests.py --check             # Check database connection
  python run_tests.py -v                  # Verbose output
  python run_tests.py --file tests/test_auth.py  # Run specific test file
  python run_tests.py --coverage          # Run with coverage report
  python run_tests.py -- -x               # Stop on first failure (pytest arg)
        """
    )
    
    # Other options
    parser.add_argument(
        '--check',
        action='store_true',
        help='Check database connections and exit'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose test output'
    )
    parser.add_argument(
        '--coverage',
        action='store_true',
        help='Generate coverage report'
    )
    parser.add_argument(
        '--file',
        help='Specific test file or directory to run'
    )
    parser.add_argument(
        'pytest_args',
        nargs=argparse.REMAINDER,
        help='Additional arguments to pass to pytest (use -- before pytest args)'
    )
    
    args = parser.parse_args()
    
    # Remove -- from pytest args if present
    if args.pytest_args and args.pytest_args[0] == '--':
        args.pytest_args = args.pytest_args[1:]
    
    # Check database connection if requested
    if args.check:
        check_database_connection()
        return 0
    
    # Run tests
    return run_tests(args)


if __name__ == '__main__':
    sys.exit(main())
