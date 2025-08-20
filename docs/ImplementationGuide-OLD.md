# Implementation Plan - Meal Planner AWS Lambda

## Overview
Building a cloud-native meal planner application using AWS Lambda, Serverless Framework, and RDS PostgreSQL. This plan focuses on Phase 1: Infrastructure Setup and Authentication, with support for local development.

## Current Status (2025-08-20)

### ✅ Completed Tasks:
- **Local Development Environment**: Flask app runs locally and connects to both Docker PostgreSQL and cloud RDS
- **AWS Infrastructure**: VPC, security groups, RDS Serverless v2, and RDS Proxy are all deployed and configured
- **Database**: Cloud RDS is seeded with test data and accessible from local environment
- **Authentication**: All auth endpoints work locally with cloud database
- **Lambda Deployment**: Flask app successfully deployed to Lambda using Serverless Framework v3.40.0
- **Environment Configuration**: All environment variables properly configured for both local and Lambda environments

### ⚠️ Current Issues:
- **Lambda Timeout**: The deployed Lambda function times out when accessing endpoints (e.g., `/api/auth/register`)
- **Root Cause**: Likely network connectivity issue between Lambda and RDS Proxy, needs investigation

### 🔄 Next Steps:
1. Debug Lambda-RDS Proxy connectivity using CloudWatch logs
2. Verify security group rules between Lambda and RDS Proxy
3. Test and fix the timeout issue
4. Complete testing of all API endpoints in Lambda environment

### Architecture Components

### AWS Infrastructure
- **VPC**: Default VPC for simplicity
- **RDS Serverless v2 PostgreSQL**: Auto-scaling database (0-1 ACU with auto-pause)
- **Lambda Functions**: Serverless compute for API endpoints
- **API Gateway**: REST API management
- **Secrets Manager**: Store database credentials and JWT secrets
- **Security Groups**: Control network access

**For detailed Lambda-RDS connection architecture, see: [Lambda-RDS-Connection.md](./Lambda-RDS-Connection.md)**

### Application Stack
- **Framework**: Serverless Framework for deployment
- **Runtime**: Python 3.11
- **Web Framework**: Flask with Blueprints
- **ORM**: SQLAlchemy
- **Validation**: Pydantic
- **Authentication**: JWT (PyJWT or flask-jwt-extended)
- **Password Hashing**: bcrypt

## Implementation Phases

### Phase 1A: Local Development with Docker PostgreSQL
1. Copy code from meal-planner-docker
2. Set up Flask application locally
3. Test with Docker PostgreSQL on port 5455
4. Verify all authentication endpoints work

### Phase 1B: Cloud RDS Testing from Local
1. Create AWS infrastructure (RDS Serverless, Security Groups)
2. Test local Flask app connecting to cloud RDS
3. Verify authentication works with cloud database

### Phase 1C: Lambda Deployment
1. Add Lambda handlers
2. Configure RDS Proxy
3. Deploy with Serverless Framework
4. Test authentication via API Gateway

## Phase 1: Infrastructure Setup and Authentication

### Step 1: AWS Infrastructure Setup

#### 1.1 VPC Strategy
We have two options for VPC:

**Option A: Use Default VPC (Simpler)**
```bash
# Get default VPC ID
export VPC_ID=$(aws ec2 describe-vpcs --filters "Name=is-default,Values=true" --query 'Vpcs[0].VpcId' --output text)
echo "Using default VPC: $VPC_ID"

# Get default subnets
export SUBNET_IDS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[*].SubnetId' --output text)
```

**Option B: Create Custom VPC (More Control)**
- Only needed if you want complete isolation
- Adds complexity for local development access
- Requires NAT Gateway for Lambda internet access ($45/month)

For this project, we'll use **Option A (Default VPC)** to simplify local development.

#### 1.2 Create Security Groups
```bash
# Get default VPC ID
export VPC_ID=$(aws ec2 describe-vpcs --filters "Name=is-default,Values=true" --query 'Vpcs[0].VpcId' --output text)

# Security group for RDS - allows access from Lambda and your local IP
aws ec2 create-security-group \
  --group-name meal-planner-rds-sg \
  --description "Security group for Meal Planner RDS database" \
  --vpc-id $VPC_ID

export RDS_SG_ID=$(aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=meal-planner-rds-sg" \
  --query 'SecurityGroups[0].GroupId' \
  --output text)

# Allow PostgreSQL access from your local IP for development
export MY_IP=$(curl -s https://checkip.amazonaws.com)
aws ec2 authorize-security-group-ingress \
  --group-id $RDS_SG_ID \
  --protocol tcp \
  --port 5432 \
  --cidr ${MY_IP}/32 \
  --group-rule-description "Local development access"

# Security group for Lambda functions
aws ec2 create-security-group \
  --group-name meal-planner-lambda-sg \
  --description "Security group for Meal Planner Lambda functions" \
  --vpc-id $VPC_ID

export LAMBDA_SG_ID=$(aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=meal-planner-lambda-sg" \
  --query 'SecurityGroups[0].GroupId' \
  --output text)

# Allow Lambda to connect to RDS
aws ec2 authorize-security-group-ingress \
  --group-id $RDS_SG_ID \
  --protocol tcp \
  --port 5432 \
  --source-group $LAMBDA_SG_ID \
  --group-rule-description "Lambda access"

# Save these IDs to .env file
echo "# Added by setup script $(date)" >> .env
echo "VPC_ID=$VPC_ID" >> .env
echo "RDS_SECURITY_GROUP_ID=$RDS_SG_ID" >> .env
echo "LAMBDA_SECURITY_GROUP_ID=$LAMBDA_SG_ID" >> .env
```

#### 1.3 Create RDS Subnet Group
```bash
# Get at least 2 subnets from different AZs (required for RDS)
export SUBNET_1=$(aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'Subnets[0].SubnetId' --output text)

export SUBNET_2=$(aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'Subnets[1].SubnetId' --output text)

# Create DB subnet group
aws rds create-db-subnet-group \
  --db-subnet-group-name meal-planner-db-subnet-group \
  --db-subnet-group-description "Subnet group for Meal Planner RDS" \
  --subnet-ids $SUBNET_1 $SUBNET_2
```

#### 1.4 Create Secrets in AWS Secrets Manager
```bash
# Generate secure passwords
export DB_PASSWORD=$(openssl rand -base64 32 | tr -d "/@\" " | cut -c1-25)
export JWT_SECRET=$(openssl rand -base64 64)
export FLASK_SECRET=$(openssl rand -base64 32)

# Store database credentials
aws secretsmanager create-secret \
  --name meal-planner/rds/credentials \
  --description "RDS database credentials for Meal Planner" \
  --secret-string "{\"username\":\"mealplanner\",\"password\":\"$DB_PASSWORD\",\"host\":\"localhost\",\"port\":5432,\"dbname\":\"mealplanner\"}"

# Store JWT secret
aws secretsmanager create-secret \
  --name meal-planner/jwt/secret \
  --description "JWT secret key for Meal Planner" \
  --secret-string "{\"secret\":\"$JWT_SECRET\"}"

# Store Flask secret key
aws secretsmanager create-secret \
  --name meal-planner/flask/secret \
  --description "Flask secret key for Meal Planner" \
  --secret-string "{\"secret\":\"$FLASK_SECRET\"}"

# Get ARNs and save to .env
export SECRET_ARN_DB=$(aws secretsmanager describe-secret --secret-id meal-planner/rds/credentials --query 'ARN' --output text)
export SECRET_ARN_JWT=$(aws secretsmanager describe-secret --secret-id meal-planner/jwt/secret --query 'ARN' --output text)
export SECRET_ARN_FLASK=$(aws secretsmanager describe-secret --secret-id meal-planner/flask/secret --query 'ARN' --output text)

echo "SECRET_ARN_DB=$SECRET_ARN_DB" >> .env
echo "SECRET_ARN_JWT=$SECRET_ARN_JWT" >> .env
echo "SECRET_ARN_FLASK=$SECRET_ARN_FLASK" >> .env

# Save passwords for local development
echo "DB_PASSWORD=$DB_PASSWORD" >> .env
echo "JWT_SECRET_KEY=$JWT_SECRET" >> .env
echo "FLASK_SECRET_KEY=$FLASK_SECRET" >> .env
```

#### 1.5 Create RDS Serverless v2 PostgreSQL Cluster

**See automated scripts:**
- [setup-networking.sh](../scripts/setup-networking.sh) - Sets up VPC and security groups
- [setup-rds-serverless.sh](../scripts/setup-rds-serverless.sh) - Creates RDS cluster
- [RDS-Setup.md](./RDS-Setup.md) - Complete RDS setup guide

```bash
# Create Aurora Serverless v2 cluster
aws rds create-db-cluster \
  --db-cluster-identifier meal-planner-cluster \
  --engine aurora-postgresql \
  --engine-version 15.4 \
  --engine-mode provisioned \
  --serverless-v2-scaling-configuration MinCapacity=0.5,MaxCapacity=2 \
  --master-username mealplanner \
  --master-user-password "$DB_PASSWORD" \
  --database-name mealplanner \
  --vpc-security-group-ids $RDS_SG_ID \
  --db-subnet-group-name meal-planner-db-subnet-group \
  --backup-retention-period 7 \
  --storage-encrypted \
  --enable-http-endpoint \
  --tags "Key=Name,Value=meal-planner-cluster" "Key=Environment,Value=dev"

# Create cluster instance
aws rds create-db-instance \
  --db-instance-identifier meal-planner-db-instance \
  --db-cluster-identifier meal-planner-cluster \
  --db-instance-class db.serverless \
  --engine aurora-postgresql \
  --publicly-accessible

# Wait for cluster to be available (this takes 5-10 minutes)
echo "Waiting for cluster to be available (this may take 5-10 minutes)..."
aws rds wait db-cluster-available --db-cluster-identifier meal-planner-cluster

# Wait for instance to be available
aws rds wait db-instance-available --db-instance-identifier meal-planner-db-instance

# Get cluster endpoint for read/write
export DB_ENDPOINT=$(aws rds describe-db-clusters \
  --db-cluster-identifier meal-planner-cluster \
  --query 'DBClusters[0].Endpoint' \
  --output text)

# Get cluster ARN for Data API access
export DB_CLUSTER_ARN=$(aws rds describe-db-clusters \
  --db-cluster-identifier meal-planner-cluster \
  --query 'DBClusters[0].DBClusterArn' \
  --output text)

echo "Database endpoint: $DB_ENDPOINT"
echo "DB_HOST=$DB_ENDPOINT" >> .env
echo "DB_CLUSTER_ARN=$DB_CLUSTER_ARN" >> .env

# Update the secret with the actual endpoint
aws secretsmanager update-secret \
  --secret-id meal-planner/rds/credentials \
  --secret-string "{\"username\":\"mealplanner\",\"password\":\"$DB_PASSWORD\",\"host\":\"$DB_ENDPOINT\",\"port\":5432,\"dbname\":\"mealplanner\"}"
```

#### 1.6 Create RDS Proxy (Recommended for Lambda)
```bash
# Create IAM role for RDS Proxy
cat > rds-proxy-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "rds.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

aws iam create-role \
  --role-name meal-planner-rds-proxy-role \
  --assume-role-policy-document file://rds-proxy-trust-policy.json

# Attach policy to access secrets
aws iam attach-role-policy \
  --role-name meal-planner-rds-proxy-role \
  --policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite

export PROXY_ROLE_ARN=$(aws iam get-role \
  --role-name meal-planner-rds-proxy-role \
  --query 'Role.Arn' --output text)

# Create RDS Proxy
aws rds create-db-proxy \
  --db-proxy-name meal-planner-proxy \
  --engine-family POSTGRESQL \
  --auth '{"AuthScheme":"SECRETS","SecretArn":"'$SECRET_ARN_DB'"}' \
  --role-arn $PROXY_ROLE_ARN \
  --vpc-subnet-ids $SUBNET_1 $SUBNET_2 \
  --vpc-security-group-ids $LAMBDA_SG_ID \
  --require-tls \
  --max-connections-percent 100 \
  --max-idle-connections-percent 50 \
  --connection-borrow-timeout 120 \
  --idle-client-timeout 1800

# Wait for proxy to be available
echo "Waiting for RDS Proxy to be available (this may take 2-3 minutes)..."
aws rds wait db-proxy-available --db-proxy-name meal-planner-proxy

# Register the database target
aws rds register-db-proxy-targets \
  --db-proxy-name meal-planner-proxy \
  --db-cluster-identifiers meal-planner-cluster

# Get Proxy endpoint
export PROXY_ENDPOINT=$(aws rds describe-db-proxies \
  --db-proxy-name meal-planner-proxy \
  --query 'DBProxies[0].Endpoint' --output text)

echo "RDS Proxy endpoint: $PROXY_ENDPOINT"
echo "RDS_PROXY_ENDPOINT=$PROXY_ENDPOINT" >> .env

# Update Lambda security group to allow connection to RDS Proxy
aws ec2 authorize-security-group-ingress \
  --group-id $RDS_SG_ID \
  --protocol tcp \
  --port 5432 \
  --source-group $LAMBDA_SG_ID \
  --group-rule-description "Lambda to RDS Proxy access"
```

### Step 2: Database Setup (Reusing Existing Schema)

#### 2.1 Copy Database Models from meal-planner-docker
```bash
# Create directory structure
mkdir -p backend/app/models
mkdir -p backend/app/schemas
mkdir -p backend/scripts

# Copy database models (manually or with cp command)
# We'll reuse the exact schema from meal-planner-docker
cp ../meal-planner-docker/backend/app/models/entities.py backend/app/models/
cp ../meal-planner-docker/backend/app/schemas/user_schemas.py backend/app/schemas/

# Copy and adapt the database rebuild script
cp ../meal-planner-docker/backend/scripts/rebuild_db.py backend/scripts/
```

#### 2.2 Database Connection Module

**See: [backend/app/database/connection.py](../backend/app/database/connection.py)**

This module handles:
- Lambda-optimized connections (NullPool)
- RDS Serverless v2 wake-up retries
- Credentials from environment or Secrets Manager

```python
"""Database configuration for Lambda (via RDS Proxy) and local development."""

import os
import json
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Define naming convention (same as meal-planner-docker)
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)
Base = declarative_base(metadata=metadata)

def get_database_url():
    """Get database URL based on environment.
    
    Connection Strategy:
    - Lambda: Connect via RDS Proxy (connection pooling managed by proxy)
    - Local Development: Direct connection to RDS cluster endpoint
    - Local Database: Connect to local PostgreSQL
    """
    
    # Check if we're running locally
    if os.getenv('IS_LOCAL', 'true').lower() == 'true':
        # LOCAL DEVELOPMENT - Direct connection
        if os.getenv('USE_LOCAL_DB', 'true').lower() == 'true':
            # Use local PostgreSQL
            return f"postgresql://{os.getenv('LOCAL_DB_USER')}:{os.getenv('LOCAL_DB_PASSWORD')}@{os.getenv('LOCAL_DB_HOST')}:{os.getenv('LOCAL_DB_PORT')}/{os.getenv('LOCAL_DB_NAME')}"
        else:
            # Use cloud RDS directly (not through proxy)
            return f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    else:
        # LAMBDA ENVIRONMENT - Use RDS Proxy
        import boto3
        secrets_client = boto3.client('secretsmanager')
        
        # Get DB credentials from Secrets Manager
        secret_response = secrets_client.get_secret_value(
            SecretId=os.environ['SECRET_ARN_DB']
        )
        db_secret = json.loads(secret_response['SecretString'])
        
        # Use RDS Proxy endpoint for Lambda
        proxy_endpoint = os.environ.get('RDS_PROXY_ENDPOINT')
        if proxy_endpoint:
            # Connect through RDS Proxy (recommended)
            return f"postgresql://{db_secret['username']}:{db_secret['password']}@{proxy_endpoint}:{db_secret['port']}/{db_secret['dbname']}"
        else:
            # Fallback to direct connection (not recommended for production)
            return f"postgresql://{db_secret['username']}:{db_secret['password']}@{db_secret['host']}:{db_secret['port']}/{db_secret['dbname']}"

def get_engine():
    """Create SQLAlchemy engine with appropriate pooling strategy."""
    
    is_lambda = os.getenv('IS_LOCAL', 'true').lower() == 'false'
    
    if is_lambda:
        # Lambda with RDS Proxy: Use NullPool since proxy handles pooling
        return create_engine(
            get_database_url(),
            poolclass=NullPool,
            connect_args={
                "connect_timeout": 10,
                "options": "-c statement_timeout=60000"  # 60 second timeout
            },
            echo=os.getenv('SQLALCHEMY_ECHO', 'false').lower() == 'true'
        )
    else:
        # Local development: Use standard connection pooling
        return create_engine(
            get_database_url(),
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,  # Verify connections before using
            pool_recycle=3600,   # Recycle connections after 1 hour
            echo=os.getenv('SQLALCHEMY_ECHO', 'false').lower() == 'true'
        )

# Create engine
engine = get_engine()

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

#### 2.3 Adapt Database Rebuild Script for Cloud
Create `backend/scripts/rebuild_db.py`:
```python
#!/usr/bin/env python3
"""
Script to initialize and seed the cloud database.
Can be run locally or as a Lambda function.

Usage:
    python backend/scripts/rebuild_db.py           # Use cloud database
    python backend/scripts/rebuild_db.py --local   # Use local database
"""

import sys
import os
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.models.database import engine, Base
from app.models.entities import *
from sqlalchemy import text
import bcrypt
from datetime import datetime, date, timedelta

# Copy all the seed functions from meal-planner-docker/backend/scripts/rebuild_db.py
# (The exact same seed_users, seed_foods, seed_meals, etc. functions)

def drop_all_tables():
    """Drop all database tables with CASCADE."""
    print("Dropping all tables...")
    with engine.connect() as conn:
        # Get all table names
        result = conn.execute(text("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public'
        """))
        tables = [row[0] for row in result]
        
        # Drop each table with CASCADE
        for table in tables:
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
    Base.metadata.create_all(bind=engine)
    print("✓ All tables created")

def main():
    """Main function to rebuild the database."""
    parser = argparse.ArgumentParser(description='Rebuild and seed the database')
    parser.add_argument('--local', action='store_true', help='Use local database')
    parser.add_argument('--action', choices=['create', 'drop', 'rebuild'], default='rebuild')
    args = parser.parse_args()
    
    # Set environment for database connection
    if args.local:
        os.environ['USE_LOCAL_DB'] = 'true'
        print("Using local database")
    else:
        os.environ['USE_LOCAL_DB'] = 'false'
        print("Using cloud database")
    
    print("\n" + "="*50)
    print("DATABASE REBUILD SCRIPT")
    print("="*50 + "\n")
    
    try:
        if args.action in ['drop', 'rebuild']:
            drop_all_tables()
        
        if args.action in ['create', 'rebuild']:
            create_all_tables()
            
            # Import here to avoid circular imports
            from sqlalchemy.orm import Session
            
            with Session(engine) as session:
                users = seed_users(session)
                foods = seed_foods(session)
                meals = seed_meals(session, foods)
                seed_meal_ingredients(session, meals, foods)
                seed_user_favorites(session, users, foods)
                seed_user_meals(session, users, meals)
                session.commit()
        
        print("\n" + "="*50)
        print("✓ DATABASE REBUILD COMPLETE!")
        print("="*50)
        print("\nTest credentials:")
        print("  Admin: admin@mealplanner.com / admin123")
        print("  User1: john.doe@example.com / password123")
        print("  User2: jane.smith@example.com / password123")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
```

### Step 3: Local Development Setup

#### 3.1 Install Dependencies
```bash
# Install uv (Python package installer - much faster than pip)
curl -LsSf https://astral.sh/uv/install.sh | sh
# Or with Homebrew: brew install uv

# Create virtual environment with uv
uv venv

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies with uv (10-100x faster than pip)
uv pip install -r backend/requirements.txt

# Or sync all dependencies (ensures exact versions)
uv pip sync backend/requirements.txt
```

#### 3.2 Create requirements.txt
```bash
cat > backend/requirements.txt << 'EOF'
# Core Flask
Flask==3.0.0
flask-cors==4.0.0
flask-jwt-extended==4.5.3

# Database
SQLAlchemy==2.0.23
psycopg2-binary==2.9.9
alembic==1.13.0

# Authentication
bcrypt==4.1.2

# Validation
pydantic==2.5.2
pydantic[email]==2.5.2
flask-pydantic==0.11.0

# AWS SDK (only needed when running in Lambda)
boto3==1.34.0

# Utilities
python-dotenv==1.0.0
python-dateutil==2.8.2
pytz==2023.3

# Development
pytest==7.4.3
pytest-flask==1.3.0
pytest-cov==4.1.0
EOF
```

#### 3.3 Test Database Connection
```bash
# Test connection to cloud database
python -c "
import os
os.environ['USE_LOCAL_DB'] = 'false'
from backend.app.models.database import engine
with engine.connect() as conn:
    result = conn.execute('SELECT version()')
    print('Connected to:', result.fetchone()[0])
"

# Initialize and seed the cloud database
cd backend
python scripts/rebuild_db.py

# Or use local database for development
python scripts/rebuild_db.py --local
```

### Step 4: Implement Authentication (Phase 1)

#### 4.1 Create Flask Application
Create `backend/app/__init__.py`:
```python
"""Flask application factory."""

import os
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_app(config_name=None):
    """Create and configure the Flask application."""
    
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'dev-jwt-secret')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 86400))
    app.config['API_PREFIX'] = os.getenv('API_PREFIX', '/api')
    
    # Initialize extensions
    CORS(app)
    JWTManager(app)
    
    # Import and register blueprints
    from app.blueprints.auth.routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix=f"{app.config['API_PREFIX']}/auth")
    
    # Health check endpoint
    @app.route('/health')
    def health():
        return {'status': 'healthy', 'environment': os.getenv('ENVIRONMENT', 'unknown')}, 200
    
    return app

# Create app instance for local development
if __name__ == '__main__':
    app = create_app()
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('LOCAL_PORT', 5000)),
        debug=os.getenv('ENVIRONMENT') == 'development'
    )
```

#### 4.2 Copy Authentication Components
```bash
# Copy authentication blueprints and services from meal-planner-docker
mkdir -p backend/app/blueprints/auth
mkdir -p backend/app/services
mkdir -p backend/app/utils

cp ../meal-planner-docker/backend/app/blueprints/auth/routes.py backend/app/blueprints/auth/
cp ../meal-planner-docker/backend/app/services/auth_service.py backend/app/services/
cp ../meal-planner-docker/backend/app/utils/jwt_utils.py backend/app/utils/
cp ../meal-planner-docker/backend/app/utils/validation.py backend/app/utils/
```

#### 4.3 Run Local Development Server
```bash
# Set environment to use cloud database
export USE_LOCAL_DB=false

# Run Flask development server
cd backend
python -m app

# Test registration endpoint
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "TestPass123",
    "full_name": "Test User",
    "sex": "OTHER",
    "address_line_1": "123 Test St",
    "city": "Test City",
    "state_province_code": "TC",
    "country_code": "US",
    "postal_code": "12345"
  }'

# Test login endpoint
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "login": "test@example.com",
    "password": "TestPass123"
  }'
```

### Step 5: Lambda Deployment (After Local Testing)

**For complete Lambda deployment guide, see: [Lambda-RDS-Connection.md](./Lambda-RDS-Connection.md#deployment-process)**

#### 5.1 Create Serverless Configuration
Create `serverless.yml`:
```yaml
service: meal-planner

provider:
  name: aws
  runtime: python3.11
  stage: ${opt:stage, 'dev'}
  region: ${env:AWS_REGION, 'us-east-1'}
  
  environment:
    ENVIRONMENT: ${self:provider.stage}
    IS_LOCAL: false
    SECRET_ARN_DB: ${env:SECRET_ARN_DB}
    SECRET_ARN_JWT: ${env:SECRET_ARN_JWT}
    SECRET_ARN_FLASK: ${env:SECRET_ARN_FLASK}
  
  vpc:
    securityGroupIds:
      - ${env:LAMBDA_SECURITY_GROUP_ID}
    subnetIds: ${env:SUBNET_IDS}
  
  iam:
    role:
      statements:
        - Effect: Allow
          Action:
            - secretsmanager:GetSecretValue
          Resource:
            - ${env:SECRET_ARN_DB}
            - ${env:SECRET_ARN_JWT}
            - ${env:SECRET_ARN_FLASK}

plugins:
  - serverless-wsgi
  - serverless-python-requirements

custom:
  wsgi:
    app: backend.app.app
    packRequirements: false
  pythonRequirements:
    dockerizePip: true
    fileName: backend/requirements.txt

functions:
  api:
    handler: wsgi_handler.handler
    events:
      - httpApi: '*'
    timeout: 30

  dbInit:
    handler: backend.handlers.db_init.handler
    timeout: 300
    description: Initialize and seed database
```

#### 5.2 Deploy to AWS

**For Serverless Framework installation and setup, see: [Serverless-Setup.md](./Serverless-Setup.md)**

```bash
# Quick deployment (after Serverless is installed)
npm install --save-dev serverless-python-requirements serverless-wsgi

# Deploy
serverless deploy --stage dev

# Get API endpoint
serverless info --stage dev
```

## Security Notes

1. **Database Access**: The RDS instance is publicly accessible but restricted by security group to:
   - Your local IP address (for development)
   - Lambda security group (for production)

2. **Secrets Management**: All sensitive data stored in AWS Secrets Manager

3. **To update your IP address** (if it changes):
```bash
# Remove old IP
aws ec2 revoke-security-group-ingress \
  --group-id $RDS_SG_ID \
  --protocol tcp \
  --port 5432 \
  --cidr YOUR_OLD_IP/32

# Add new IP
export MY_IP=$(curl -s https://checkip.amazonaws.com)
aws ec2 authorize-security-group-ingress \
  --group-id $RDS_SG_ID \
  --protocol tcp \
  --port 5432 \
  --cidr ${MY_IP}/32
```

## Cost Estimates

**With RDS Serverless v2 (0-1 ACU, auto-pause):**
- **RDS Serverless v2**: ~$1-2/month when mostly paused (storage only)
- **Lambda**: < $1/month for development
- **Secrets Manager**: $0.40/secret/month = $1.20/month
- **API Gateway**: < $1/month for development
- **Total**: ~$5/month for light development use

**See [Lambda-RDS-Connection.md](./Lambda-RDS-Connection.md#cost-considerations) for detailed cost breakdown**

## Next Steps

### Phase 2: Complete Authentication
- Password reset functionality
- Email verification
- Refresh tokens

### Phase 3: Food Catalog
- CRUD operations for foods
- Search and filtering

### Phase 4: Meal Planning
- Meal CRUD operations
- Meal scheduling
- Nutritional calculations

## Troubleshooting

### Database Connection Issues
1. Check security group allows your IP: `aws ec2 describe-security-groups --group-ids $RDS_SG_ID`
2. Verify RDS is publicly accessible: `aws rds describe-db-instances --db-instance-identifier meal-planner-db`
3. Test with psql: `psql -h $DB_ENDPOINT -U mealplanner -d mealplanner`

### Local Development Issues
1. Ensure .env file is properly configured
2. Check USE_LOCAL_DB setting
3. Verify virtual environment is activated
4. Check PostgreSQL is running (if using local DB)
