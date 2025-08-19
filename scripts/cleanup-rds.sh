#!/bin/bash

# Cleanup RDS Serverless v2 and related resources
# WARNING: This will DELETE all data!

set -e

# Configuration
REGION="us-east-1"
AWS_PROFILE="serverless-cli-user"
CLUSTER_NAME="meal-planner-cluster"
SUBNET_GROUP_NAME="meal-planner-subnet-group"
SECURITY_GROUP_NAME="meal-planner-rds-sg"

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${RED}==========================================="
echo "WARNING: RDS Cleanup Script"
echo "==========================================="
echo "This will DELETE:"
echo "  - RDS Cluster: $CLUSTER_NAME"
echo "  - All database data (no backup!)"
echo "  - Security group: $SECURITY_GROUP_NAME"
echo "  - Subnet group: $SUBNET_GROUP_NAME"
echo "==========================================${NC}"
echo ""
read -p "Are you sure you want to delete everything? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Cleanup cancelled."
    exit 0
fi

echo ""
echo -e "${YELLOW}Step 1: Deleting RDS instance${NC}"
aws rds delete-db-instance \
    --profile $AWS_PROFILE \
    --region $REGION \
    --db-instance-identifier "${CLUSTER_NAME}-instance-1" \
    --skip-final-snapshot \
    --delete-automated-backups \
    2>/dev/null && echo "✓ Instance deletion started" || echo "Instance not found or already deleted"

echo ""
echo -e "${YELLOW}Step 2: Deleting RDS cluster${NC}"
aws rds delete-db-cluster \
    --profile $AWS_PROFILE \
    --region $REGION \
    --db-cluster-identifier $CLUSTER_NAME \
    --skip-final-snapshot \
    2>/dev/null && echo "✓ Cluster deletion started" || echo "Cluster not found or already deleted"

echo ""
echo -e "${YELLOW}Step 3: Waiting for cluster deletion (this may take a few minutes)${NC}"
echo "Waiting..."
aws rds wait db-cluster-deleted \
    --profile $AWS_PROFILE \
    --region $REGION \
    --db-cluster-identifier $CLUSTER_NAME \
    2>/dev/null || echo "Cluster already deleted or not found"

echo ""
echo -e "${YELLOW}Step 4: Deleting subnet group${NC}"
aws rds delete-db-subnet-group \
    --profile $AWS_PROFILE \
    --region $REGION \
    --db-subnet-group-name $SUBNET_GROUP_NAME \
    2>/dev/null && echo "✓ Subnet group deleted" || echo "Subnet group not found or already deleted"

echo ""
echo -e "${YELLOW}Step 5: Getting security group ID${NC}"
SG_ID=$(aws ec2 describe-security-groups \
    --profile $AWS_PROFILE \
    --region $REGION \
    --filters "Name=group-name,Values=$SECURITY_GROUP_NAME" \
    --query 'SecurityGroups[0].GroupId' \
    --output text 2>/dev/null || echo "")

if [ ! -z "$SG_ID" ] && [ "$SG_ID" != "None" ]; then
    echo "Found security group: $SG_ID"
    echo ""
    echo -e "${YELLOW}Step 6: Deleting security group${NC}"
    aws ec2 delete-security-group \
        --profile $AWS_PROFILE \
        --region $REGION \
        --group-id $SG_ID \
        2>/dev/null && echo "✓ Security group deleted" || echo "Could not delete security group (may be in use)"
else
    echo "Security group not found"
fi

echo ""
echo -e "${GREEN}==========================================="
echo "✓ RDS Cleanup Complete!"
echo "==========================================${NC}"
echo ""
echo "All AWS resources have been deleted."
echo "You can now run ./scripts/setup-rds-serverless.sh to create fresh resources."
echo ""
echo -e "${YELLOW}Note: Your .env file still contains the old configuration.${NC}"
echo "The setup script will update it with new values when you run it."
