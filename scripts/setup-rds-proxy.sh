#!/bin/bash

# Script to set up RDS Proxy for Lambda connection pooling
# This proxy sits between Lambda and RDS Serverless v2 for better connection management

set -e  # Exit on error

# Configuration
PROFILE="${AWS_PROFILE:-serverless-cli-user}"
REGION="${AWS_REGION:-us-east-1}"
PROXY_NAME="meal-planner-proxy"
CLUSTER_ID="meal-planner-cluster"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up RDS Proxy for Lambda connection pooling...${NC}"

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    exit 1
fi

# Load values from .env
source .env

# Check required environment variables
if [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ] || [ -z "$LAMBDA_SECURITY_GROUP_ID" ] || [ -z "$PRIVATE_SUBNET_1A" ] || [ -z "$PRIVATE_SUBNET_1B" ]; then
    echo -e "${RED}Error: Missing required environment variables in .env${NC}"
    echo "Required: DB_USER, DB_PASSWORD, LAMBDA_SECURITY_GROUP_ID, PRIVATE_SUBNET_1A, PRIVATE_SUBNET_1B"
    exit 1
fi

# Get the secret ARN (we'll create a secret for RDS Proxy)
echo -e "${YELLOW}Creating/updating secret for RDS Proxy...${NC}"
SECRET_NAME="rds-proxy-secret-meal-planner"

# Check if secret exists
SECRET_ARN=$(aws secretsmanager describe-secret \
    --secret-id "$SECRET_NAME" \
    --profile "$PROFILE" \
    --region "$REGION" \
    --query 'ARN' \
    --output text 2>/dev/null || echo "")

if [ -z "$SECRET_ARN" ]; then
    # Create new secret
    SECRET_ARN=$(aws secretsmanager create-secret \
        --name "$SECRET_NAME" \
        --description "Credentials for RDS Proxy to connect to meal-planner RDS cluster" \
        --secret-string "{\"username\":\"$DB_USER\",\"password\":\"$DB_PASSWORD\"}" \
        --profile "$PROFILE" \
        --region "$REGION" \
        --query 'ARN' \
        --output text)
    echo -e "${GREEN}Created new secret: $SECRET_ARN${NC}"
else
    # Update existing secret
    aws secretsmanager update-secret \
        --secret-id "$SECRET_NAME" \
        --secret-string "{\"username\":\"$DB_USER\",\"password\":\"$DB_PASSWORD\"}" \
        --profile "$PROFILE" \
        --region "$REGION" > /dev/null
    echo -e "${GREEN}Updated existing secret: $SECRET_ARN${NC}"
fi

# Create IAM role for RDS Proxy
echo -e "${YELLOW}Creating IAM role for RDS Proxy...${NC}"
ROLE_NAME="rds-proxy-role-meal-planner"

# Check if role exists
ROLE_ARN=$(aws iam get-role \
    --role-name "$ROLE_NAME" \
    --profile "$PROFILE" \
    --query 'Role.Arn' \
    --output text 2>/dev/null || echo "")

if [ -z "$ROLE_ARN" ]; then
    # Create trust policy
    TRUST_POLICY=$(cat <<EOF
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
)

    # Create role
    ROLE_ARN=$(aws iam create-role \
        --role-name "$ROLE_NAME" \
        --assume-role-policy-document "$TRUST_POLICY" \
        --profile "$PROFILE" \
        --query 'Role.Arn' \
        --output text)
    
    # Attach policy for Secrets Manager access
    aws iam attach-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-arn "arn:aws:iam::aws:policy/SecretsManagerReadWrite" \
        --profile "$PROFILE"
    
    echo -e "${GREEN}Created IAM role: $ROLE_ARN${NC}"
    
    # Wait for role to propagate
    echo "Waiting 10 seconds for IAM role to propagate..."
    sleep 10
else
    echo -e "${GREEN}Using existing IAM role: $ROLE_ARN${NC}"
fi

# Check if RDS Proxy already exists
echo -e "${YELLOW}Checking for existing RDS Proxy...${NC}"
PROXY_EXISTS=$(aws rds describe-db-proxies \
    --db-proxy-name "$PROXY_NAME" \
    --profile "$PROFILE" \
    --region "$REGION" \
    --query 'DBProxies[0].DBProxyName' \
    --output text 2>/dev/null || echo "")

if [ "$PROXY_EXISTS" == "$PROXY_NAME" ]; then
    echo -e "${YELLOW}RDS Proxy already exists. Getting endpoint...${NC}"
    PROXY_ENDPOINT=$(aws rds describe-db-proxies \
        --db-proxy-name "$PROXY_NAME" \
        --profile "$PROFILE" \
        --region "$REGION" \
        --query 'DBProxies[0].Endpoint' \
        --output text)
else
    # Create RDS Proxy
    echo -e "${YELLOW}Creating RDS Proxy...${NC}"
    aws rds create-db-proxy \
        --db-proxy-name "$PROXY_NAME" \
        --engine-family POSTGRESQL \
        --auth '[{"AuthScheme":"SECRETS","SecretArn":"'$SECRET_ARN'"}]' \
        --role-arn "$ROLE_ARN" \
        --vpc-subnet-ids "$PRIVATE_SUBNET_1A" "$PRIVATE_SUBNET_1B" \
        --vpc-security-group-ids "$LAMBDA_SECURITY_GROUP_ID" \
        --require-tls \
        --idle-client-timeout 1800 \
        --profile "$PROFILE" \
        --region "$REGION" > /dev/null
    
    echo "Waiting for RDS Proxy to be created (this can take 5-10 minutes)..."
    
    # Wait for proxy to be available
    while true; do
        STATUS=$(aws rds describe-db-proxies \
            --db-proxy-name "$PROXY_NAME" \
            --profile "$PROFILE" \
            --region "$REGION" \
            --query 'DBProxies[0].Status' \
            --output text 2>/dev/null || echo "creating")
        
        if [ "$STATUS" == "available" ]; then
            break
        elif [ "$STATUS" == "failed" ]; then
            echo -e "${RED}RDS Proxy creation failed${NC}"
            exit 1
        fi
        
        echo -n "."
        sleep 10
    done
    
    echo ""
    PROXY_ENDPOINT=$(aws rds describe-db-proxies \
        --db-proxy-name "$PROXY_NAME" \
        --profile "$PROFILE" \
        --region "$REGION" \
        --query 'DBProxies[0].Endpoint' \
        --output text)
    
    echo -e "${GREEN}RDS Proxy created successfully!${NC}"
fi

# Register the RDS cluster with the proxy
echo -e "${YELLOW}Registering RDS cluster with proxy...${NC}"

# Get cluster resource ID
CLUSTER_RESOURCE_ID=$(aws rds describe-db-clusters \
    --db-cluster-identifier "$CLUSTER_ID" \
    --profile "$PROFILE" \
    --region "$REGION" \
    --query 'DBClusters[0].DbClusterResourceId' \
    --output text)

# Check if target already exists
TARGET_EXISTS=$(aws rds describe-db-proxy-targets \
    --db-proxy-name "$PROXY_NAME" \
    --profile "$PROFILE" \
    --region "$REGION" \
    --query "Targets[?RdsResourceId=='$CLUSTER_RESOURCE_ID'].RdsResourceId" \
    --output text 2>/dev/null || echo "")

if [ -z "$TARGET_EXISTS" ]; then
    # Register proxy target
    aws rds register-db-proxy-targets \
        --db-proxy-name "$PROXY_NAME" \
        --db-cluster-identifiers "$CLUSTER_ID" \
        --profile "$PROFILE" \
        --region "$REGION" > /dev/null
    
    echo -e "${GREEN}Registered RDS cluster with proxy${NC}"
else
    echo -e "${GREEN}RDS cluster already registered with proxy${NC}"
fi

# Update .env with proxy endpoint
echo -e "${YELLOW}Updating .env with RDS Proxy endpoint...${NC}"

# Check if RDS_PROXY_ENDPOINT already exists in .env
if grep -q "^RDS_PROXY_ENDPOINT=" .env; then
    # Update existing entry
    sed -i.bak "s|^RDS_PROXY_ENDPOINT=.*|RDS_PROXY_ENDPOINT=$PROXY_ENDPOINT|" .env
else
    # Add new entry
    echo "" >> .env
    echo "# RDS Proxy endpoint for Lambda connections" >> .env
    echo "RDS_PROXY_ENDPOINT=$PROXY_ENDPOINT" >> .env
fi

echo -e "${GREEN}✅ RDS Proxy setup complete!${NC}"
echo ""
echo -e "${GREEN}Proxy Details:${NC}"
echo "  Name: $PROXY_NAME"
echo "  Endpoint: $PROXY_ENDPOINT"
echo "  Port: 5432"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Update your Lambda to use RDS_PROXY_ENDPOINT instead of DB_HOST"
echo "2. In serverless.yml, you can set:"
echo "   DB_HOST: \${env:RDS_PROXY_ENDPOINT}"
echo "3. Redeploy Lambda with: serverless deploy"
echo ""
echo -e "${GREEN}For Lambda, the database connection will be:${NC}"
echo "  postgresql://$DB_USER:****@$PROXY_ENDPOINT:5432/$DB_NAME"
