# Lambda Deployment Scripts

This directory contains scripts for deploying the Flask application to AWS Lambda.

## Scripts

- **`deploy-lambda.sh`** - Production deployment script using Docker to build ARM64 packages
- **`test-lambda-local.sh`** - Test the Lambda package locally using Docker before deployment

## Directory Structure

### Local Development Structure
```
meal-planner-aws-lambda/
├── backend/
│   ├── app/                    # Flask application source
│   │   ├── __init__.py         # Flask app factory
│   │   ├── config.py           # Configuration management
│   │   ├── requirements.txt    # Python dependencies (reference)
│   │   ├── blueprints/         # API endpoints
│   │   │   └── auth/           # Authentication endpoints
│   │   ├── models/             # Database models
│   │   │   ├── database.py     # SQLAlchemy setup
│   │   │   └── entities.py     # ORM models
│   │   ├── schemas/            # Pydantic validation schemas
│   │   ├── services/           # Business logic layer
│   │   └── utils/              # Utility functions
│   └── scripts/
│       └── deployment/         # Deployment scripts
├── serverless.yml              # Serverless Framework config
└── .env                        # Local environment variables
```

### Lambda Deployment Package Structure
```
/var/task/                      # Lambda function root
├── wsgi_handler.py             # Lambda entry point
├── app/                        # Flask application (copied from backend/app)
│   ├── __init__.py            # Flask app factory
│   ├── config.py              # Configuration
│   ├── blueprints/            # API endpoints
│   │   └── auth/              # Authentication
│   ├── models/                # Database models
│   ├── schemas/               # Validation schemas
│   ├── services/              # Business logic
│   └── utils/                 # Utilities
├── Flask/                     # Flask package
├── flask_cors/                # Flask-CORS package
├── flask_jwt_extended/        # JWT package
├── flask_sqlalchemy/          # SQLAlchemy integration
├── flask_pydantic/            # Pydantic integration
├── sqlalchemy/                # SQLAlchemy ORM
├── psycopg2/                  # PostgreSQL driver
├── pydantic/                  # Data validation
├── bcrypt/                    # Password hashing
├── jwt/                       # JWT library
├── email_validator/           # Email validation
├── dotenv/                    # Environment variables
├── serverless_wsgi/           # Lambda WSGI adapter
└── werkzeug/                  # WSGI utilities
```

## Key Points

1. **Application Root**: In Lambda, the Flask app is imported as `from app import create_app`
2. **Handler Location**: The Lambda handler is at `/var/task/wsgi_handler.py`
3. **Dependencies**: All Python packages are installed at the root level (`/var/task/`)
4. **Architecture**: Packages are built for ARM64 (Graviton2) using Docker

## Environment Variables Required in Lambda

```bash
# Flask Configuration
FLASK_SECRET_KEY=<your-secret-key>
JWT_SECRET_KEY=<your-jwt-secret>
JWT_ACCESS_TOKEN_EXPIRES=3600

# Database Configuration (via RDS Proxy)
DB_USER=<database-username>
DB_PASSWORD=<database-password>
DB_HOST=<rds-proxy-endpoint>
DB_PORT=5432
DB_NAME=<database-name>

# AWS Lambda automatically sets
AWS_LAMBDA_FUNCTION_NAME=<function-name>
AWS_REGION=<region>
```

## Usage

### Test Locally
```bash
# From project root
./backend/scripts/deployment/test-lambda-local.sh
```

### Deploy to Lambda
```bash
# From project root
./backend/scripts/deployment/deploy-lambda.sh
```

## Dependencies

All dependencies are explicitly listed in the deployment scripts:

- **Flask Framework**: Flask, Flask-Cors, Flask-JWT-Extended, Flask-SQLAlchemy, flask-pydantic
- **Database**: SQLAlchemy, psycopg2-binary
- **Authentication**: bcrypt, PyJWT, pydantic, email-validator
- **Lambda**: serverless-wsgi, Werkzeug
- **Utilities**: python-dotenv

## Notes

- The scripts use Docker to ensure ARM64 compatibility
- Test files and `__pycache__` directories are excluded from deployment
- The package size is typically 15-20MB
- Lambda cold starts are minimized by using ARM64 architecture
