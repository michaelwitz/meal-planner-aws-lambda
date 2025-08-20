# Lambda Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the Flask Meal Planner application to AWS Lambda. We use a hybrid approach:
- **Serverless Framework**: For infrastructure management (Lambda configuration, API Gateway, VPC, environment variables)
- **Custom Docker-based deployment script**: For packaging and deploying the application code

## Architecture Decisions

### Why Custom Deployment Script?

While Serverless Framework is excellent for infrastructure management, we encountered several challenges with its packaging system:

1. **Import Path Issues**: Serverless Framework's packaging created complex nested structures that broke Python imports
2. **Docker Dependency**: The serverless-python-requirements plugin requires Docker, adding complexity
3. **Layer Management**: Automatic layer creation was inconsistent and hard to debug
4. **Path Manipulation**: Required complex PYTHONPATH configurations and wsgi_handler adjustments

### Our Solution

We use Serverless Framework for what it does best (infrastructure) and a custom script for what we control best (packaging):
- Serverless manages: Lambda configuration, API Gateway, VPC, security groups, environment variables
- Custom script handles: Building the deployment package with correct structure using Docker

## Prerequisites

1. **AWS CLI configured** with appropriate credentials
2. **Docker installed** and running (for building Lambda-compatible packages)
3. **Node.js and npm** (for Serverless Framework)
4. **Python 3.11** (matching Lambda runtime)

## Project Structure

```
meal-planner-aws-lambda/
├── backend/
│   ├── app/                    # Flask application code
│   │   ├── __init__.py         # App factory
│   │   ├── config.py           # Configuration
│   │   ├── models/             # SQLAlchemy models
│   │   ├── routes/             # API endpoints
│   │   └── utils/              # Utilities
│   └── scripts/
│       └── deployment/         # Deployment scripts
│           ├── deploy-lambda.sh
│           ├── test-lambda-local.sh
│           └── README.md
├── serverless.yml              # Infrastructure configuration
└── docs/                       # Documentation
```

## Step-by-Step Deployment

### Step 1: Infrastructure Setup with Serverless

1. **Install Serverless Framework**:
```bash
npm install -g serverless
npm install  # Install project dependencies
```

2. **Deploy infrastructure** (first time only):
```bash
serverless deploy --stage test
```

This creates:
- Lambda function configuration
- API Gateway
- VPC configuration
- Security groups
- Environment variables
- IAM roles

### Step 2: Configure Security Groups

The Lambda function and RDS Proxy must communicate within the VPC. Fix the security group if needed:

```bash
# Get the security group ID (usually sg-0fd605efde80bd711 for test)
aws lambda get-function-configuration \
  --function-name meal-planner-test-app \
  --region us-east-1 \
  --query 'VpcConfig.SecurityGroupIds[0]' \
  --output text

# Add ingress rule for PostgreSQL (port 5432)
aws ec2 authorize-security-group-ingress \
  --group-id <SECURITY_GROUP_ID> \
  --protocol tcp \
  --port 5432 \
  --source-group <SAME_SECURITY_GROUP_ID> \
  --region us-east-1
```

### Step 3: Deploy Application Code

Use the custom deployment script:

```bash
cd backend/scripts/deployment
./deploy-lambda.sh
```

This script:
1. Creates a clean package directory
2. Copies the Flask app maintaining correct structure
3. Uses Docker with Lambda Python image to install dependencies
4. Creates wsgi_handler.py at the root
5. Zips everything and uploads to Lambda
6. Updates the Lambda handler configuration

## Deployment Script Details

### What the Script Does

```bash
#!/bin/bash
# Key operations:

1. Package Structure:
   /var/task/
   ├── wsgi_handler.py      # Lambda handler (imports from app)
   ├── app/                 # Your Flask application
   │   ├── __init__.py
   │   ├── config.py
   │   └── ...
   └── [dependencies]       # All Python packages

2. Docker Build:
   - Uses official Lambda Python 3.11 ARM64 image
   - Installs all dependencies in Lambda-compatible environment
   - Ensures binary compatibility (psycopg2, pydantic-core, etc.)

3. Handler Configuration:
   - Sets handler to wsgi_handler.handler
   - wsgi_handler imports from app package (not backend.app)
```

### Manual Deployment (if needed)

If the script fails, you can deploy manually:

```bash
# 1. Build package
mkdir -p lambda-package-temp/app
cp -r backend/app/* lambda-package-temp/app/

# 2. Create handler
cat > lambda-package-temp/wsgi_handler.py << 'EOF'
import serverless_wsgi
from app import create_app

app = create_app()

def handler(event, context):
    return serverless_wsgi.handle_request(app, event, context)
EOF

# 3. Install dependencies with Docker
docker run --rm \
  -v $(pwd)/lambda-package-temp:/var/task \
  -w /var/task \
  --entrypoint /bin/bash \
  public.ecr.aws/lambda/python:3.11-arm64 \
  -c "pip install Flask==3.0.0 Flask-Cors==6.0.0 Flask-JWT-Extended==4.5.3 \
      Flask-SQLAlchemy==3.1.1 flask-pydantic==0.11.0 SQLAlchemy==2.0.23 \
      psycopg2-binary==2.9.9 bcrypt==4.1.2 PyJWT==2.10.1 pydantic==2.5.2 \
      pydantic-core==2.14.5 email-validator==2.1.0 python-dotenv==1.0.0 \
      serverless-wsgi==3.0.3 Werkzeug==3.0.1 -t ."

# 4. Create ZIP
cd lambda-package-temp
zip -r ../lambda-package.zip .
cd ..

# 5. Deploy
aws lambda update-function-code \
  --function-name meal-planner-test-app \
  --zip-file fileb://lambda-package.zip \
  --region us-east-1

# 6. Update handler
aws lambda update-function-configuration \
  --function-name meal-planner-test-app \
  --handler wsgi_handler.handler \
  --region us-east-1
```

## Testing the Deployment

### 1. Health Check
```bash
curl https://c557ywae4j.execute-api.us-east-1.amazonaws.com/test/health
# Expected: {"status":"healthy"}
```

### 2. Database Connection
```bash
curl https://c557ywae4j.execute-api.us-east-1.amazonaws.com/test/test-db
# Expected: {"status":"ok","message":"Database connection successful!",...}
```

### 3. Check Logs
```bash
aws logs tail /aws/lambda/meal-planner-test-app --region us-east-1 --since 5m
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Import Errors (`No module named 'app'`)
- **Cause**: Wrong package structure or handler path
- **Solution**: Ensure handler is `wsgi_handler.handler` and app is at `/var/task/app/`

#### 2. Database Connection Timeout (30s)
- **Cause**: Security group missing ingress rules
- **Solution**: Add self-referencing rule on port 5432 (see Step 2)

#### 3. Binary Incompatibility Errors
- **Cause**: Dependencies built on Mac instead of Linux
- **Solution**: Always use Docker with Lambda base image for building

#### 4. Missing Dependencies
- **Cause**: Incomplete requirements or failed pip install
- **Solution**: Check Docker build output, ensure all packages are listed

#### 5. Handler Not Found
- **Cause**: Serverless Framework overwrote the handler setting
- **Solution**: Run update-function-configuration after deployment

### Verifying Deployment

Check current Lambda configuration:
```bash
aws lambda get-function-configuration \
  --function-name meal-planner-test-app \
  --region us-east-1 \
  --query '{Handler:Handler,Runtime:Runtime,Arch:Architectures[0],VPC:VpcConfig.VpcId}' \
  --output json
```

Expected output:
```json
{
  "Handler": "wsgi_handler.handler",
  "Runtime": "python3.11",
  "Arch": "arm64",
  "VPC": "vpc-0d7c669258adcbb31"
}
```

## Environment-Specific Configuration

### Test Environment
- Lambda: `meal-planner-test-app`
- API Gateway: `test-meal-planner`
- Stage: `test`
- Endpoint: `https://c557ywae4j.execute-api.us-east-1.amazonaws.com/test/`

### Production Environment
- Lambda: `meal-planner-production-app`
- API Gateway: `production-meal-planner`
- Stage: `production`
- Endpoint: Configure in serverless.yml and update script

## CI/CD Integration

To integrate with GitHub Actions or other CI/CD:

1. Store AWS credentials as secrets
2. Install Docker in CI environment
3. Run deployment script on merge to main:

```yaml
# .github/workflows/deploy.yml
name: Deploy to Lambda
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: aws-actions/configure-aws-credentials@v1
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      - run: |
          cd backend/scripts/deployment
          ./deploy-lambda.sh
```

## Summary

This hybrid approach gives us:
- **Reliable deployments**: Consistent package structure every time
- **Full control**: We know exactly what's in the deployment package
- **Docker compatibility**: Dependencies built in Lambda-like environment
- **Simple debugging**: Clear structure makes issues easy to identify
- **Infrastructure as Code**: Serverless manages all AWS resources

The key insight is using each tool for its strengths: Serverless for infrastructure, custom scripts for packaging.
