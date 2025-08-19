#!/bin/bash

# Setup RDS Serverless v2 PostgreSQL with public access for local development
# Region: us-east-1 (N. Virginia)

set -e

# Configuration
REGION="us-east-1"
AWS_PROFILE="serverless-cli-user"
CLUSTER_NAME="meal-planner-cluster"  # AWS RDS identifier (hyphens allowed)
DB_NAME="meal_planner"                # PostgreSQL database name (underscores only)
DB_USER="meal_planner_admin"          # PostgreSQL username (underscores only)
SUBNET_GROUP_NAME="meal-planner-subnet-group"  # AWS resource (hyphens allowed)
SECURITY_GROUP_NAME="meal-planner-rds-sg"      # AWS resource (hyphens allowed)

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=========================================="
echo "RDS Serverless v2 Setup (us-east-1)"
echo "=========================================="
echo "Using AWS Profile: $AWS_PROFILE"
echo ""

echo -e "${YELLOW}Step 1: Getting your current IP${NC}"
MY_IP=$(curl -s https://checkip.amazonaws.com)
echo "Your IP: $MY_IP"

echo ""
echo -e "${YELLOW}Step 2: Getting default VPC${NC}"
DEFAULT_VPC=$(aws ec2 describe-vpcs \
    --profile $AWS_PROFILE \
    --region $REGION \
    --filters "Name=is-default,Values=true" \
    --query "Vpcs[0].VpcId" \
    --output text)

if [ "$DEFAULT_VPC" = "None" ] || [ -z "$DEFAULT_VPC" ]; then
    echo -e "${RED}Error: No default VPC found${NC}"
    echo "Creating default VPC..."
    aws ec2 create-default-vpc --profile $AWS_PROFILE --region $REGION
    DEFAULT_VPC=$(aws ec2 describe-vpcs \
        --profile $AWS_PROFILE \
        --region $REGION \
        --filters "Name=is-default,Values=true" \
        --query "Vpcs[0].VpcId" \
        --output text)
fi
echo "VPC ID: $DEFAULT_VPC"

echo ""
echo -e "${YELLOW}Step 3: Getting RDS Security Group${NC}"

# First check if RDS_SECURITY_GROUP_ID is in .env
if [ -f .env ] && grep -q "^RDS_SECURITY_GROUP_ID=" .env; then
    SG_ID=$(grep "^RDS_SECURITY_GROUP_ID=" .env | cut -d'=' -f2 | tr -d '\n\r')
    if [ ! -z "$SG_ID" ] && [ "$SG_ID" != "" ]; then
        echo "Using security group from .env: $SG_ID"
        # Verify it exists
        aws ec2 describe-security-groups \
            --profile $AWS_PROFILE \
            --region $REGION \
            --group-ids $SG_ID \
            --output text > /dev/null 2>&1
        if [ $? -ne 0 ]; then
            echo -e "${RED}Error: Security group $SG_ID not found in AWS${NC}"
            echo "Please run ./scripts/setup-networking.sh first"
            exit 1
        fi
    else
        echo -e "${RED}Error: RDS_SECURITY_GROUP_ID is empty in .env${NC}"
        echo "Please run ./scripts/setup-networking.sh first"
        exit 1
    fi
else
    echo -e "${RED}Error: RDS_SECURITY_GROUP_ID not found in .env${NC}"
    echo "Please run ./scripts/setup-networking.sh first to set up networking"
    exit 1
fi

echo ""
echo -e "${YELLOW}Step 4: Verifying security group rules${NC}"
echo "Security group $SG_ID should already have rules from setup-networking.sh"
echo "Checking current rules..."
aws ec2 describe-security-groups \
    --profile $AWS_PROFILE \
    --region $REGION \
    --group-ids $SG_ID \
    --query 'SecurityGroups[0].IpPermissions[*].[FromPort,IpRanges[0].CidrIp]' \
    --output text | while read port cidr; do
    echo "  • Port $port open to $cidr"
done

echo ""
echo -e "${YELLOW}Step 5: Getting subnets${NC}"
SUBNET_IDS=$(aws ec2 describe-subnets \
    --profile $AWS_PROFILE \
    --region $REGION \
    --filters "Name=vpc-id,Values=$DEFAULT_VPC" \
    --query "Subnets[*].SubnetId" \
    --output text)
echo "Subnets: $(echo $SUBNET_IDS | wc -w) found"

echo ""
echo -e "${YELLOW}Step 6: Creating DB subnet group${NC}"
aws rds create-db-subnet-group \
    --profile $AWS_PROFILE \
    --region $REGION \
    --db-subnet-group-name $SUBNET_GROUP_NAME \
    --db-subnet-group-description "Subnet group for meal planner RDS" \
    --subnet-ids $SUBNET_IDS \
    2>/dev/null && echo "✓ Created subnet group" || echo "Subnet group already exists"

echo ""
echo -e "${YELLOW}Step 7: Generating secure password${NC}"
# Check if DB_PASSWORD exists in .env
if [ -f .env ] && grep -q "DB_PASSWORD=" .env; then
    # Extract password and remove any trailing spaces or comments
    DB_PASSWORD=$(grep "DB_PASSWORD=" .env | cut -d'=' -f2 | cut -d' ' -f1 | cut -d'#' -f1 | tr -d '\n\r')
    echo "Using password from .env file"
else
    # Generate a clean 8-character password (AWS RDS requirements: 8-128 chars, ASCII only)
    # Using only alphanumeric to avoid special character issues
    DB_PASSWORD=$(openssl rand -hex 4)
    echo "Generated new password (8 characters, alphanumeric)"
    echo ""
    echo -e "${RED}IMPORTANT: Save this password to your .env file:${NC}"
    echo "DB_PASSWORD=$DB_PASSWORD"
fi

# Validate password doesn't have control characters
if echo "$DB_PASSWORD" | grep -q '[[:cntrl:]]'; then
    echo -e "${RED}Error: Password contains control characters. Please set a clean password in .env${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Step 8: Creating RDS Serverless v2 cluster${NC}"
echo "This will take 5-10 minutes..."

# Check if cluster already exists
EXISTING_CLUSTER=$(aws rds describe-db-clusters \
    --profile $AWS_PROFILE \
    --region $REGION \
    --db-cluster-identifier $CLUSTER_NAME \
    --query 'DBClusters[0].DBClusterIdentifier' \
    --output text 2>/dev/null || echo "")

if [ -z "$EXISTING_CLUSTER" ]; then
    # Aurora PostgreSQL 15.10 supports MinCapacity=0 with auto-pause
    # Using dev/test configuration for cost savings
    echo "Creating Aurora Serverless v2 PostgreSQL 15.10 with auto-pause..."
    
    aws rds create-db-cluster \
        --profile $AWS_PROFILE \
        --region $REGION \
        --db-cluster-identifier $CLUSTER_NAME \
        --engine aurora-postgresql \
        --engine-version 15.10 \
        --engine-mode provisioned \
        --serverless-v2-scaling-configuration MinCapacity=0,MaxCapacity=1 \
        --master-username $DB_USER \
        --master-user-password "$DB_PASSWORD" \
        --database-name $DB_NAME \
        --db-subnet-group-name $SUBNET_GROUP_NAME \
        --vpc-security-group-ids $SG_ID \
        --backup-retention-period 1 \
        --preferred-backup-window "03:00-04:00" \
        --preferred-maintenance-window "mon:04:00-mon:05:00" \
        --enable-http-endpoint \
        --tags "Key=Environment,Value=dev" "Key=Template,Value=dev-test"
    
    echo "✓ Cluster creation started"
else
    echo "Cluster already exists"
fi

echo ""
echo -e "${YELLOW}Step 9: Creating DB instance${NC}"
aws rds create-db-instance \
    --profile $AWS_PROFILE \
    --region $REGION \
    --db-instance-identifier "${CLUSTER_NAME}-instance-1" \
    --db-cluster-identifier $CLUSTER_NAME \
    --db-instance-class db.serverless \
    --engine aurora-postgresql \
    --publicly-accessible \
    2>/dev/null && echo "✓ Instance creation started" || echo "Instance already exists"

echo ""
echo -e "${YELLOW}Step 10: Waiting for cluster to be available${NC}"
echo "This takes 5-10 minutes. You can press Ctrl+C and check status later with:"
echo "aws rds describe-db-clusters --profile $AWS_PROFILE --region $REGION --db-cluster-identifier $CLUSTER_NAME --query 'DBClusters[0].Status'"
echo ""
echo "Waiting..."

aws rds wait db-cluster-available \
    --profile $AWS_PROFILE \
    --region $REGION \
    --db-cluster-identifier $CLUSTER_NAME

echo ""
echo -e "${YELLOW}Step 11: Getting endpoint${NC}"
ENDPOINT=$(aws rds describe-db-clusters \
    --profile $AWS_PROFILE \
    --region $REGION \
    --db-cluster-identifier $CLUSTER_NAME \
    --query 'DBClusters[0].Endpoint' \
    --output text)

echo ""
echo -e "${YELLOW}Step 12: Updating .env file${NC}"

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
        echo "  ✓ Updated: ${key}"
    else
        # Key doesn't exist, check if it should exist based on .env.example
        if grep -q "^${key}=" .env.example 2>/dev/null; then
            # Add it after a comment or at the end of the database section
            echo "${key}=${value}" >> "$file"
            echo "  ✓ Added: ${key}"
        fi
    fi
}

# Update .env file with RDS configuration
echo "Updating .env file with RDS configuration..."
update_env "DB_HOST" "$ENDPOINT"
update_env "DB_PORT" "5432"
update_env "DB_NAME" "$DB_NAME"
update_env "DB_USER" "$DB_USER"
update_env "DB_PASSWORD" "$DB_PASSWORD"
update_env "RDS_SECURITY_GROUP_ID" "$SG_ID"

# Also update USE_LOCAL_DB to false since we just set up cloud DB
update_env "USE_LOCAL_DB" "false"

echo -e "${GREEN}✓ .env file updated successfully${NC}"

echo ""
echo -e "${GREEN}=========================================="
echo "✓ RDS Serverless v2 Setup Complete!"
echo "==========================================${NC}"
echo ""
echo "RDS Configuration has been saved to .env:"
echo ""
echo "  Cluster: $CLUSTER_NAME"
echo "  Host: $ENDPOINT"
echo "  Database: $DB_NAME"
echo "  Username: $DB_USER"
echo "  Password: [hidden - saved in .env]"
echo "  Security Group: $SG_ID"
echo ""
echo -e "${YELLOW}Note: USE_LOCAL_DB has been set to 'false' to use cloud database${NC}"
echo ""
echo "Next steps:"
echo "1. Test the connection:"
echo "   cd backend"
echo "   source ../.venv/bin/activate"
echo "   python scripts/rebuild_db.py"
echo ""
echo "2. Run the Flask app:"
echo "   python -m app"
echo ""
echo -e "${GREEN}Your RDS is now accessible from your laptop!${NC}"
echo ""
echo -e "${YELLOW}Database will auto-pause after 15 min of inactivity (costs ~$0 when paused)${NC}"
echo -e "${YELLOW}First connection after pause takes 15-30 seconds to wake up${NC}"
echo -e "${YELLOW}Monthly cost when paused: ~$1-2 (storage only)${NC}"
