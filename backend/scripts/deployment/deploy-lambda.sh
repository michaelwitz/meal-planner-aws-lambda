#!/bin/bash

# Exit on error
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Docker-based Lambda deployment...${NC}"

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
PROJECT_ROOT="$(dirname "$BACKEND_DIR")"

# Change to project root
cd "$PROJECT_ROOT"

# Variables
FUNCTION_NAME="meal-planner-test-app"
ZIP_FILE="lambda-package.zip"
TEMP_DIR="lambda-package-temp"

# Clean up any previous builds
echo -e "${YELLOW}🧹 Cleaning up previous builds...${NC}"
rm -rf $TEMP_DIR $ZIP_FILE

# Create temporary directory structure
echo -e "${YELLOW}📁 Creating package directory structure...${NC}"
mkdir -p $TEMP_DIR/app

# Copy application code
echo -e "${YELLOW}📦 Copying application code...${NC}"
cp -r backend/app/* $TEMP_DIR/app/

# Remove test files and __pycache__
echo -e "${YELLOW}🧹 Removing unnecessary files...${NC}"
find $TEMP_DIR -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find $TEMP_DIR -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
find $TEMP_DIR -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find $TEMP_DIR -name "*.pyc" -delete 2>/dev/null || true
find $TEMP_DIR -name ".DS_Store" -delete 2>/dev/null || true
rm -f $TEMP_DIR/app/requirements.txt 2>/dev/null || true

# Create wsgi_handler.py
echo -e "${YELLOW}📝 Creating wsgi_handler.py...${NC}"
cat > $TEMP_DIR/wsgi_handler.py << 'EOF'
"""Lambda handler for Flask app."""
import serverless_wsgi
from app import create_app

# Create Flask app instance
app = create_app()

def handler(event, context):
    """Lambda handler function."""
    return serverless_wsgi.handle_request(app, event, context)
EOF

# Create comprehensive requirements.txt with ALL dependencies
echo -e "${YELLOW}📋 Creating requirements.txt with all dependencies...${NC}"
cat > $TEMP_DIR/requirements.txt << 'EOF'
# Core Flask and extensions
Flask==3.0.0
Flask-Cors==6.0.0
Flask-JWT-Extended==4.5.3
Flask-SQLAlchemy==3.1.1
flask-pydantic==0.11.0

# Database
SQLAlchemy==2.0.23
psycopg2-binary==2.9.9

# Authentication and validation
bcrypt==4.1.2
PyJWT==2.10.1
pydantic==2.5.2
pydantic-core==2.14.5
email-validator==2.1.0

# Utilities
python-dotenv==1.0.0

# Lambda specific
serverless-wsgi==3.0.3
Werkzeug==3.0.1
EOF

# Build the Lambda package using Docker
echo -e "${YELLOW}🐳 Building Lambda package in Docker (ARM64)...${NC}"
docker run --rm \
  -v $(pwd)/$TEMP_DIR:/var/task \
  -w /var/task \
  --entrypoint /bin/bash \
  public.ecr.aws/lambda/python:3.11-arm64 \
  -c "
    echo '📦 Installing dependencies for Lambda ARM64...'
    pip install --no-cache-dir -r requirements.txt -t . --upgrade
    echo '✅ Dependencies installed successfully'
  "

# Create the deployment package
echo -e "${YELLOW}📦 Creating deployment package...${NC}"
cd $TEMP_DIR
zip -rq ../$ZIP_FILE . \
  -x "*.pyc" \
  -x "*__pycache__*" \
  -x "*.pytest_cache*" \
  -x "*/tests/*" \
  -x ".DS_Store" \
  -x "*.dist-info/*" \
  -x "*.egg-info/*"
cd ..

# Get the size of the package
PACKAGE_SIZE=$(ls -lh $ZIP_FILE | awk '{print $5}')
echo -e "${GREEN}📦 Package size: $PACKAGE_SIZE${NC}"

# Deploy to Lambda
echo -e "${YELLOW}🚀 Deploying to AWS Lambda...${NC}"
aws lambda update-function-code \
  --function-name $FUNCTION_NAME \
  --zip-file fileb://$ZIP_FILE \
  --architectures arm64 \
  --region us-east-1

# Update the handler configuration
echo -e "${YELLOW}🔧 Updating handler configuration...${NC}"
aws lambda update-function-configuration \
  --function-name $FUNCTION_NAME \
  --handler wsgi_handler.handler \
  --region us-east-1

# Wait for the update to complete
echo -e "${YELLOW}⏳ Waiting for Lambda function to update...${NC}"
aws lambda wait function-updated \
  --function-name $FUNCTION_NAME \
  --region us-east-1

# Get function status
echo -e "${YELLOW}📊 Getting function status...${NC}"
aws lambda get-function \
  --function-name $FUNCTION_NAME \
  --region us-east-1 \
  --query 'Configuration.[FunctionName, Runtime, Handler, State, LastUpdateStatus, Architectures[0]]' \
  --output table

# Clean up
echo -e "${YELLOW}🧹 Cleaning up temporary files...${NC}"
rm -rf $TEMP_DIR $ZIP_FILE

echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""
echo -e "${GREEN}Test your deployment with:${NC}"
echo "  curl https://YOUR_API_GATEWAY_URL/health"
echo ""
echo -e "${YELLOW}Note: The app structure in Lambda is:${NC}"
echo "  /var/task/app/        - Your Flask application"
echo "  /var/task/wsgi_handler.py - Lambda handler"
echo "  /var/task/[dependencies]  - All Python packages"
