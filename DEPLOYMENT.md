# Quick Start Deployment Guide

## Overview

Quick deployment instructions for the Meal Planner Flask application to AWS Lambda.

**For detailed documentation, see:**
- [Complete Implementation Guide](docs/ImplementationGuide.md) - Full architecture and design
- [Lambda Deployment Details](docs/Lambda-Deployment.md) - Step-by-step Lambda deployment
- [Serverless Setup](docs/Serverless-Setup.md) - Infrastructure management
- [RDS Setup](docs/RDS-Setup.md) - Database configuration

## Prerequisites

1. **AWS CLI** configured with appropriate credentials
2. **Docker** installed and running (required for Lambda package building)
3. **Node.js and npm** installed (for Serverless Framework)
4. **Python 3.11** installed (matching Lambda runtime)

## Quick Deployment Steps

### 1. Initial Setup (First Time Only)

```bash
# Clone the repository
git clone https://github.com/your-repo/meal-planner-aws-lambda.git
cd meal-planner-aws-lambda

# Install Serverless Framework v3
npm install -g serverless@3

# Install project dependencies
npm install --legacy-peer-deps
```

### 2. Deploy Infrastructure (First Time)

```bash
# Deploy AWS infrastructure with Serverless
serverless deploy --stage test

# This creates Lambda function, API Gateway, VPC, security groups, etc.
```

### 3. Configure Security Group

```bash
# Get security group ID
SG_ID=$(aws lambda get-function-configuration \
  --function-name meal-planner-test-app \
  --region us-east-1 \
  --query 'VpcConfig.SecurityGroupIds[0]' \
  --output text)

# Add ingress rule for RDS Proxy (if not already added)
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 5432 \
  --source-group $SG_ID \
  --region us-east-1 2>/dev/null || echo "Rule already exists"
```

### 4. Deploy Application Code

```bash
# Use custom deployment script
cd backend/scripts/deployment
./deploy-lambda.sh

# This script:
# - Builds Lambda-compatible package with Docker
# - Maintains correct Python import paths
# - Installs all dependencies
# - Creates ZIP and uploads to Lambda
```

### 5. Verify Deployment

```bash
# Test health endpoint
curl https://c557ywae4j.execute-api.us-east-1.amazonaws.com/test/health
# Expected: {"status":"healthy"}

# Test database connection
curl https://c557ywae4j.execute-api.us-east-1.amazonaws.com/test/test-db
# Expected: {"status":"ok","message":"Database connection successful!",...}

# Check Lambda logs if needed
aws logs tail /aws/lambda/meal-planner-test-app --region us-east-1 --since 5m
```

## Serverless Framework Usage

We use Serverless Framework for:
- Initial Lambda function creation
- API Gateway setup
- Environment variable management
- VPC configuration

We DON'T use it for:
- Package building (it preserves `/backend` structure which we don't want)
- Deployment (we use AWS CLI directly)

## Package Structure

```
/var/task/                  # Lambda root
├── wsgi_handler.py        # Entry point
├── app/                   # Flask application (NO backend prefix)
│   ├── __init__.py       # Flask factory
│   ├── config.py         # Configuration
│   ├── blueprints/       # API routes
│   ├── models/           # Database models
│   ├── schemas/          # Validation
│   ├── services/         # Business logic
│   └── utils/            # Utilities
└── [dependencies]        # All Python packages
```

## Database Connectivity Issues

### Current Problem
- Lambda times out (30s) when trying to connect to RDS via RDS Proxy
- Lambda is in VPC with correct subnets and security group
- RDS Proxy endpoint is configured in environment variables

### Possible Causes
1. Security group rules between Lambda and RDS Proxy
2. RDS Proxy not accessible from Lambda subnets
3. IAM authentication issues
4. Network ACLs blocking traffic

### Next Steps
1. Verify security group rules allow traffic from Lambda to RDS Proxy on port 5432
2. Check RDS Proxy is in same VPC/subnets as Lambda
3. Verify RDS Proxy target health
4. Check CloudWatch logs for RDS Proxy

## Environment Variables

Required in Lambda:
- `AWS_LAMBDA_FUNCTION_NAME` (set automatically)
- `FLASK_SECRET_KEY`
- `JWT_SECRET_KEY`
- `JWT_ACCESS_TOKEN_EXPIRES`
- `DB_HOST` (RDS Proxy endpoint)
- `DB_PORT` (5432)
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`

## GitHub Actions CI/CD

To be implemented using the manual process above.
