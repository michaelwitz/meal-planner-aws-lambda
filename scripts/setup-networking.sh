#!/bin/bash

# Setup networking resources (VPC, Security Groups) for RDS and Lambda
# This should be run BEFORE setup-rds-serverless.sh

set -e

# Configuration
REGION="us-east-1"
AWS_PROFILE="serverless-cli-user"
RDS_SECURITY_GROUP_NAME="meal-planner-rds-sg"
LAMBDA_SECURITY_GROUP_NAME="meal-planner-lambda-sg"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "==========================================="
echo "Networking Setup for Meal Planner"
echo "==========================================="
echo "Using AWS Profile: $AWS_PROFILE"
echo "Region: $REGION"
echo ""

# Function to update or add a key-value pair in .env
update_env() {
    local key=$1
    local value=$2
    local file=".env"
    
    if [ ! -f "$file" ]; then
        echo -e "${YELLOW}Creating .env from .env.example...${NC}"
        cp .env.example .env
    fi
    
    if grep -q "^${key}=" "$file"; then
        # Key exists, update it (works on both Mac and Linux)
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' "s|^${key}=.*|${key}=${value}|" "$file"
        else
            # Linux
            sed -i "s|^${key}=.*|${key}=${value}|" "$file"
        fi
        echo "  ✓ Updated: ${key}=${value}"
    else
        # Key doesn't exist, add it
        echo "${key}=${value}" >> "$file"
        echo "  ✓ Added: ${key}=${value}"
    fi
}

echo -e "${YELLOW}Step 1: Getting your current IP${NC}"
MY_IP=$(curl -s https://checkip.amazonaws.com)
echo "Your IP: $MY_IP"

echo ""
echo -e "${YELLOW}Step 2: Getting/Creating default VPC${NC}"
DEFAULT_VPC=$(aws ec2 describe-vpcs \
    --profile $AWS_PROFILE \
    --region $REGION \
    --filters "Name=is-default,Values=true" \
    --query "Vpcs[0].VpcId" \
    --output text 2>/dev/null || echo "None")

if [ "$DEFAULT_VPC" = "None" ] || [ -z "$DEFAULT_VPC" ]; then
    echo "No default VPC found. Creating one..."
    aws ec2 create-default-vpc --profile $AWS_PROFILE --region $REGION
    DEFAULT_VPC=$(aws ec2 describe-vpcs \
        --profile $AWS_PROFILE \
        --region $REGION \
        --filters "Name=is-default,Values=true" \
        --query "Vpcs[0].VpcId" \
        --output text)
    echo "✓ Created default VPC: $DEFAULT_VPC"
else
    echo "✓ Using existing VPC: $DEFAULT_VPC"
fi

# Get VPC CIDR for later use
VPC_CIDR=$(aws ec2 describe-vpcs \
    --profile $AWS_PROFILE \
    --region $REGION \
    --vpc-ids $DEFAULT_VPC \
    --query "Vpcs[0].CidrBlock" \
    --output text)
echo "  VPC CIDR: $VPC_CIDR"

echo ""
echo -e "${YELLOW}Step 3: Creating/Finding RDS Security Group${NC}"

# Check if RDS security group exists
RDS_SG_ID=$(aws ec2 describe-security-groups \
    --profile $AWS_PROFILE \
    --region $REGION \
    --filters "Name=group-name,Values=$RDS_SECURITY_GROUP_NAME" \
    --query 'SecurityGroups[0].GroupId' \
    --output text 2>/dev/null || echo "None")

if [ "$RDS_SG_ID" = "None" ] || [ -z "$RDS_SG_ID" ]; then
    echo "Creating new RDS security group..."
    RDS_SG_ID=$(aws ec2 create-security-group \
        --profile $AWS_PROFILE \
        --region $REGION \
        --group-name $RDS_SECURITY_GROUP_NAME \
        --description "RDS access for meal planner (local dev + Lambda)" \
        --vpc-id $DEFAULT_VPC \
        --query 'GroupId' \
        --output text)
    echo "✓ Created RDS security group: $RDS_SG_ID"
else
    echo "✓ Using existing RDS security group: $RDS_SG_ID"
fi

echo ""
echo -e "${YELLOW}Step 4: Adding RDS Security Group Rules${NC}"

# Allow PostgreSQL from your current IP
echo "Adding rule for your IP ($MY_IP)..."
aws ec2 authorize-security-group-ingress \
    --profile $AWS_PROFILE \
    --region $REGION \
    --group-id $RDS_SG_ID \
    --protocol tcp \
    --port 5432 \
    --cidr ${MY_IP}/32 \
    2>/dev/null && echo "  ✓ Added rule for your IP" || echo "  • Rule for your IP already exists"

# Allow PostgreSQL from VPC (for Lambda)
echo "Adding rule for VPC CIDR ($VPC_CIDR)..."
aws ec2 authorize-security-group-ingress \
    --profile $AWS_PROFILE \
    --region $REGION \
    --group-id $RDS_SG_ID \
    --protocol tcp \
    --port 5432 \
    --cidr $VPC_CIDR \
    2>/dev/null && echo "  ✓ Added rule for VPC" || echo "  • Rule for VPC already exists"

echo ""
echo -e "${YELLOW}Step 5: Creating/Finding Lambda Security Group${NC}"

# Check if Lambda security group exists
LAMBDA_SG_ID=$(aws ec2 describe-security-groups \
    --profile $AWS_PROFILE \
    --region $REGION \
    --filters "Name=group-name,Values=$LAMBDA_SECURITY_GROUP_NAME" \
    --query 'SecurityGroups[0].GroupId' \
    --output text 2>/dev/null || echo "None")

if [ "$LAMBDA_SG_ID" = "None" ] || [ -z "$LAMBDA_SG_ID" ]; then
    echo "Creating new Lambda security group..."
    LAMBDA_SG_ID=$(aws ec2 create-security-group \
        --profile $AWS_PROFILE \
        --region $REGION \
        --group-name $LAMBDA_SECURITY_GROUP_NAME \
        --description "Lambda functions for meal planner" \
        --vpc-id $DEFAULT_VPC \
        --query 'GroupId' \
        --output text)
    echo "✓ Created Lambda security group: $LAMBDA_SG_ID"
else
    echo "✓ Using existing Lambda security group: $LAMBDA_SG_ID"
fi

echo ""
echo -e "${YELLOW}Step 6: Adding Lambda Security Group Rules${NC}"

# Allow all outbound traffic from Lambda (default, but let's be explicit)
echo "Adding outbound rules for Lambda..."
aws ec2 authorize-security-group-egress \
    --profile $AWS_PROFILE \
    --region $REGION \
    --group-id $LAMBDA_SG_ID \
    --protocol all \
    --cidr 0.0.0.0/0 \
    2>/dev/null && echo "  ✓ Added outbound rule" || echo "  • Outbound rule already exists"

echo ""
echo -e "${YELLOW}Step 7: Getting Subnet Information${NC}"

# Get subnet IDs for the VPC
SUBNET_IDS=$(aws ec2 describe-subnets \
    --profile $AWS_PROFILE \
    --region $REGION \
    --filters "Name=vpc-id,Values=$DEFAULT_VPC" \
    --query "Subnets[*].SubnetId" \
    --output text)

# Get first two subnets (typically in different AZs)
SUBNET_ARRAY=($SUBNET_IDS)
SUBNET_1="${SUBNET_ARRAY[0]}"
SUBNET_2="${SUBNET_ARRAY[1]}"

echo "Found ${#SUBNET_ARRAY[@]} subnets"
echo "  Subnet 1: $SUBNET_1"
echo "  Subnet 2: $SUBNET_2"

echo ""
echo -e "${YELLOW}Step 8: Updating .env file${NC}"

update_env "VPC_ID" "$DEFAULT_VPC"
update_env "RDS_SECURITY_GROUP_ID" "$RDS_SG_ID"
update_env "LAMBDA_SECURITY_GROUP_ID" "$LAMBDA_SG_ID"
update_env "PRIVATE_SUBNET_1A" "$SUBNET_1"
update_env "PRIVATE_SUBNET_1B" "$SUBNET_2"

echo ""
echo -e "${GREEN}==========================================="
echo "✓ Networking Setup Complete!"
echo "==========================================${NC}"
echo ""
echo "Configuration saved to .env:"
echo "  VPC: $DEFAULT_VPC"
echo "  RDS Security Group: $RDS_SG_ID"
echo "  Lambda Security Group: $LAMBDA_SG_ID"
echo "  Subnets: ${#SUBNET_ARRAY[@]} available"
echo ""
echo "Security Rules configured:"
echo "  • RDS accessible from your IP: $MY_IP"
echo "  • RDS accessible from VPC CIDR: $VPC_CIDR"
echo "  • Lambda can access RDS within VPC"
echo ""
echo -e "${GREEN}Next step: Run ./scripts/setup-rds-serverless.sh${NC}"
