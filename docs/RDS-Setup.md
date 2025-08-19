# RDS Serverless v2 Setup Guide

## Overview

This guide explains how to set up AWS RDS Serverless v2 PostgreSQL that can be accessed by:
1. **Local development** from your laptop
2. **AWS Lambda functions** when deployed

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     AWS us-east-1 Region                     │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                    Default VPC                        │  │
│  │                                                       │  │
│  │  ┌─────────────────────────────────────────────┐    │  │
│  │  │   RDS Serverless v2 PostgreSQL              │    │  │
│  │  │   - Public endpoint                         │    │  │
│  │  │   - Auto-scales: 0-1 ACU (pauses when idle) │    │  │
│  │  │   - Port: 5432                              │    │  │
│  │  └─────────────────────────────────────────────┘    │  │
│  │                          ▲                           │  │
│  │                          │                           │  │
│  │  ┌───────────────┐      │      ┌────────────────┐  │  │
│  │  │Security Group │◀─────┴──────│  Lambda        │  │  │
│  │  │               │              │  (Future)      │  │  │
│  │  │Rules:         │              └────────────────┘  │  │
│  │  │- Your IP      │                                   │  │
│  │  │- VPC CIDR     │                                   │  │
│  │  └───────────────┘                                   │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ Internet
                              │
                    ┌─────────────────┐
                    │  Your Laptop     │
                    │  (Baltimore)     │
                    └─────────────────┘
```

## Quick Setup

### Prerequisites
- AWS CLI installed and configured
- AWS account with appropriate permissions
- `.env` file created from `.env.example`

### Run the Setup Script

```bash
# Make the script executable
chmod +x scripts/setup-rds-serverless.sh

# Run the setup
./scripts/setup-rds-serverless.sh
```

The script will:
1. Create a security group with rules for your IP and VPC
2. Create an RDS Serverless v2 cluster (PostgreSQL 15.10)
3. Configure auto-scaling (0-1 ACU, auto-pauses when idle after 15 min)
4. Enable public access for local development
5. Output connection details for your `.env` file

**Password Requirements:**
- 8-128 characters
- Only ASCII printable characters
- Cannot contain: `/`, `@`, `"`, or spaces
- Script generates an 8-character alphanumeric password by default

### Update Your .env File

After the script completes, add the output to your `.env`:

```bash
# AWS RDS Configuration
DB_HOST=meal-planner-cluster.cluster-xxxxx.us-east-1.rds.amazonaws.com
DB_PORT=5432
DB_NAME=mealplanner
DB_USER=mealplanner_admin
DB_PASSWORD=<your-password>
RDS_SECURITY_GROUP_ID=sg-xxxxx
```

## Testing the Connection

### 1. Initialize the Cloud Database

```bash
cd backend
source ../.venv/bin/activate
export USE_LOCAL_DB=false
python scripts/rebuild_db.py
```

### 2. Test with psql (Optional)

```bash
# Load environment variables
source .env

# Connect with psql
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME

# Test query
\dt  # List tables
SELECT * FROM "USER";
\q   # Quit
```

### 3. Run Flask with Cloud Database

```bash
cd backend
export USE_LOCAL_DB=false
python -m app
```

Test the API:
```bash
curl -X POST http://localhost:5050/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login": "admin@mealplanner.com", "password": "admin123"}'
```

## Managing Access

### Update Your IP Address

If your IP changes (new location, different network):

```bash
# Get your new IP
MY_IP=$(curl -s https://checkip.amazonaws.com)
echo "Your IP: $MY_IP"

# Update security group
aws ec2 authorize-security-group-ingress \
  --region us-east-1 \
  --group-id $RDS_SECURITY_GROUP_ID \
  --protocol tcp \
  --port 5432 \
  --cidr ${MY_IP}/32
```

### Remove Old IP

```bash
# Remove old IP
aws ec2 revoke-security-group-ingress \
  --region us-east-1 \
  --group-id $RDS_SECURITY_GROUP_ID \
  --protocol tcp \
  --port 5432 \
  --cidr OLD_IP/32
```

## Cost Management

### RDS Serverless v2 Pricing (us-east-1)
- **When Paused (0 ACU)**: 
  - **Compute**: $0/hour (automatically pauses after ~15 min of inactivity)
  - **Storage only**: ~$0.10/GB-month (so ~$0.10-$1/month for small DBs)
- **When Active**:
  - **0.5 ACU**: ~$0.06/hour (~$43/month if running 24/7)
  - **1 ACU**: ~$0.12/hour (~$86/month if running 24/7)
- **Wake-up time**: 15-30 seconds when scaling from 0 ACUs
- **Backups**: 7 days retention included

### Stop/Start Cluster (Save Money)

```bash
# Stop cluster (saves compute costs, keeps data)
aws rds stop-db-cluster \
  --region us-east-1 \
  --db-cluster-identifier meal-planner-cluster

# Start cluster
aws rds start-db-cluster \
  --region us-east-1 \
  --db-cluster-identifier meal-planner-cluster
```

## Database Management

### Switch Between Local and Cloud

```bash
# Use local Docker PostgreSQL
export USE_LOCAL_DB=true
cd backend && python -m app

# Use cloud RDS Serverless
export USE_LOCAL_DB=false
cd backend && python -m app
```

### View Cluster Status

```bash
aws rds describe-db-clusters \
  --region us-east-1 \
  --db-cluster-identifier meal-planner-cluster \
  --query 'DBClusters[0].{Status:Status,Endpoint:Endpoint}'
```

## Lambda Deployment (Future)

When you deploy to Lambda, it will automatically use the RDS because:
1. Lambda will run in the same VPC
2. Security group already allows VPC CIDR
3. Lambda will use environment variables for connection

The Serverless Framework deployment will handle this automatically.

## Troubleshooting

### Connection Timeout
- Check your IP is in security group: `aws ec2 describe-security-groups --region us-east-1 --group-ids $RDS_SECURITY_GROUP_ID`
- Ensure cluster is running: `aws rds describe-db-clusters --region us-east-1 --db-cluster-identifier meal-planner-cluster --query 'DBClusters[0].Status'`

### Authentication Failed
- Verify password in `.env` matches what was used during creation
- Check username is correct: `mealplanner_admin`

### Database Not Found
- Ensure database name is `mealplanner`
- Run rebuild_db.py to create tables

## Clean Up (Remove Everything)

```bash
# Delete RDS cluster (this will delete all data!)
aws rds delete-db-cluster \
  --region us-east-1 \
  --db-cluster-identifier meal-planner-cluster \
  --skip-final-snapshot

# Delete security group
aws ec2 delete-security-group \
  --region us-east-1 \
  --group-id $RDS_SECURITY_GROUP_ID

# Delete subnet group
aws rds delete-db-subnet-group \
  --region us-east-1 \
  --db-subnet-group-name meal-planner-subnet-group
```
