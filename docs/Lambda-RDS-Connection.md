# Lambda to RDS Serverless v2 Connection Guide

## Overview

This guide explains how AWS Lambda functions connect to RDS Serverless v2 PostgreSQL and how to configure the Serverless Framework deployment.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      AWS us-east-1                           │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │                    Default VPC                         │  │
│  │                                                        │  │
│  │  ┌─────────────────┐      ┌──────────────────────┐    │  │
│  │  │                 │      │                      │    │  │
│  │  │  Lambda         │─────▶│  RDS Serverless v2   │    │  │
│  │  │  Functions      │      │  PostgreSQL 15.10    │    │  │
│  │  │                 │      │  (0-1 ACU)           │    │  │
│  │  └─────────────────┘      └──────────────────────┘    │  │
│  │         │                           ▲                  │  │
│  │         │                           │                  │  │
│  │         ▼                           │                  │  │
│  │  ┌─────────────────┐      ┌────────────────────┐      │  │
│  │  │  Environment    │      │  AWS Secrets       │      │  │
│  │  │  Variables      │      │  Manager           │      │  │
│  │  └─────────────────┘      └────────────────────┘      │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

## Connection Strategy

### Why RDS Serverless v2 is Perfect for Lambda

1. **Auto-scaling**: Scales from 0 to 1 ACU based on demand
2. **Cost-effective**: Pauses after 15 minutes of inactivity (costs ~$0)
3. **Wake-up time**: 15-30 seconds from cold (acceptable for most APIs)
4. **No connection limit issues**: Scales with your Lambda concurrency

### Connection Methods

| Method | Use Case | Configuration |
|--------|----------|---------------|
| **Direct Connection** | Development, Low traffic | Lambda → RDS directly |
| **RDS Proxy** | Production, High concurrency | Lambda → RDS Proxy → RDS |
| **Secrets Manager** | All environments | Secure credential storage |

## File Structure

```
backend/
├── app/
│   ├── handlers/
│   │   ├── api_handler.py      # Main Lambda handler
│   │   └── db_init.py          # Database initialization
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py       # Database connection logic
│   │   └── session.py          # Session management
│   ├── blueprints/             # API routes
│   ├── models/                 # SQLAlchemy models
│   └── config.py               # Configuration
├── scripts/                    # Local scripts (NOT deployed)
│   ├── rebuild_db.py
│   ├── deploy-lambda.sh
│   └── test-connection.py
├── serverless.yml              # Serverless Framework config
├── requirements.txt            # Python dependencies
└── package.json               # Serverless plugins
```

## Implementation Files

### 1. Database Connection Module

See: `backend/app/database/connection.py`

This module handles:
- Credential retrieval (env vars or Secrets Manager)
- SQLAlchemy engine creation with NullPool
- Connection retry logic for cold starts

### 2. Lambda Handler

See: `backend/app/handlers/api_handler.py`

Main handler that:
- Initializes database connection
- Routes requests to Flask app
- Handles Lambda context and events

### 3. Configuration

See: `backend/app/config.py`

Manages different configurations:
- Lambda environment detection
- Local vs cloud database switching
- Connection pooling settings

## Serverless Framework Configuration

### Basic serverless.yml Structure

```yaml
service: meal-planner-api

provider:
  name: aws
  runtime: python3.11
  region: us-east-1
  
  # Lambda must be in same VPC as RDS
  vpc:
    securityGroupIds:
      - ${env:LAMBDA_SECURITY_GROUP_ID}
    subnetIds:
      - ${env:PRIVATE_SUBNET_1A}
      - ${env:PRIVATE_SUBNET_1B}

# Exclude scripts and tests from deployment
package:
  patterns:
    - '!scripts/**'
    - '!tests/**'
    - '!**/__pycache__/**'
    - '!**/*.pyc'

functions:
  api:
    handler: app.handlers.api_handler.handler
    timeout: 30
    environment:
      DB_HOST: ${env:DB_HOST}
      DB_PORT: ${env:DB_PORT}
      DB_NAME: ${env:DB_NAME}
      DB_USER: ${env:DB_USER}
      DB_PASSWORD: ${env:DB_PASSWORD}
```

## Deployment Process

### 1. Set Environment Variables

```bash
# Load from .env file
source .env
export DB_HOST DB_PORT DB_NAME DB_USER DB_PASSWORD
export LAMBDA_SECURITY_GROUP_ID PRIVATE_SUBNET_1A PRIVATE_SUBNET_1B
```

### 2. Deploy with Serverless

```bash
# Install dependencies
npm install

# Deploy to AWS
serverless deploy --stage dev
```

### 3. Test the Deployment

```bash
# Test endpoint
curl https://your-api-id.execute-api.us-east-1.amazonaws.com/dev/api/health

# View logs
serverless logs -f api -t
```

## Security Best Practices

### Option 1: Environment Variables (Simple)
- Good for development
- Store credentials in Lambda environment variables
- Easy to update via Serverless Framework

### Option 2: AWS Secrets Manager (Recommended)
- Secure credential storage
- Automatic rotation capability
- Audit trail

To use Secrets Manager:
1. Store credentials in Secrets Manager
2. Grant Lambda IAM permission to read secret
3. Update `app/database/connection.py` to fetch from Secrets Manager

## Performance Optimization

### For RDS Serverless v2:

1. **Connection Pooling**: Use `NullPool` in SQLAlchemy (no pooling)
2. **Timeout Settings**: Set appropriate connection timeout (5 seconds)
3. **Retry Logic**: Implement retry for cold starts
4. **Statement Timeout**: Set max query execution time

### For Lambda:

1. **Memory**: Allocate sufficient memory (512MB minimum)
2. **Timeout**: Set appropriate timeout (30 seconds for API)
3. **Reserved Concurrency**: Consider setting for predictable scaling
4. **VPC Configuration**: Ensure proper subnet and security group setup

## Monitoring

### CloudWatch Metrics to Track:

- Lambda invocations and errors
- Lambda duration and cold starts
- RDS connections count
- RDS ACU usage
- Database query performance

### Useful Commands:

```bash
# Check RDS status
aws rds describe-db-clusters \
  --db-cluster-identifier meal-planner-cluster \
  --query 'DBClusters[0].Status'

# View Lambda logs
serverless logs -f api --startTime 1h

# Check Lambda metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=meal-planner-api-dev-api \
  --start-time 2024-01-19T00:00:00Z \
  --end-time 2024-01-19T23:59:59Z \
  --period 3600 \
  --statistics Average
```

## Troubleshooting

### Common Issues:

1. **Lambda timeout connecting to RDS**
   - Check VPC configuration
   - Verify security groups
   - Ensure RDS is not paused (wait 15-30s)

2. **Too many connections error**
   - Verify using NullPool
   - Check Lambda concurrency
   - Consider RDS Proxy

3. **Cold start delays**
   - Normal for first request after pause
   - Consider keeping Lambda warm
   - Use provisioned concurrency for critical APIs

## Cost Considerations

### RDS Serverless v2:
- **Paused**: ~$0/hour (storage only ~$0.10/GB/month)
- **Active**: $0.12/ACU-hour
- **Auto-pauses**: After 15 minutes of inactivity

### Lambda:
- **Requests**: $0.20 per 1M requests
- **Duration**: $0.0000166667 per GB-second
- **Free tier**: 1M requests, 400,000 GB-seconds per month

## Next Steps

1. Create Lambda handler code in `app/handlers/`
2. Set up Secrets Manager for production
3. Configure RDS Proxy for high-traffic scenarios
4. Implement monitoring and alerting
5. Add automated testing for Lambda functions
