#!/bin/bash

# Exit on error
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🧪 Testing Lambda package locally with Docker...${NC}"

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
PROJECT_ROOT="$(dirname "$BACKEND_DIR")"

# Change to project root
cd "$PROJECT_ROOT"

# Variables
TEMP_DIR="lambda-package-temp"
IMAGE_NAME="meal-planner-lambda-test"

# Clean up any previous builds
echo -e "${YELLOW}🧹 Cleaning up previous builds...${NC}"
rm -rf $TEMP_DIR
docker rmi $IMAGE_NAME 2>/dev/null || true

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

# Create comprehensive requirements.txt
echo -e "${YELLOW}📋 Creating requirements.txt...${NC}"
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

# Show the structure that will be deployed
echo -e "${GREEN}📂 Structure to be deployed to Lambda:${NC}"
echo "/"
echo "├── wsgi_handler.py          # Lambda entry point"
echo "├── app/                     # Flask application root"
echo "│   ├── __init__.py         # Flask app factory"
echo "│   ├── config.py           # Configuration"
echo "│   ├── blueprints/         # API endpoints"
echo "│   │   └── auth/           # Authentication endpoints"
echo "│   ├── models/             # Database models"
echo "│   │   ├── database.py"
echo "│   │   └── entities.py"
echo "│   ├── schemas/            # Pydantic schemas"
echo "│   ├── services/           # Business logic"
echo "│   └── utils/              # Utilities"
echo "└── [dependencies]          # All Python packages installed at root"
echo ""

# Create Dockerfile
echo -e "${YELLOW}🐳 Creating Dockerfile...${NC}"
cat > $TEMP_DIR/Dockerfile << 'EOF'
FROM public.ecr.aws/lambda/python:3.11-arm64

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /var/task/

# Set the handler
CMD ["wsgi_handler.handler"]
EOF

# Build Docker image
echo -e "${YELLOW}🐳 Building Docker image...${NC}"
docker build -t $IMAGE_NAME $TEMP_DIR

# Show actual structure in container
echo -e "${GREEN}📂 Actual structure in Lambda container:${NC}"
docker run --rm \
  -e AWS_LAMBDA_FUNCTION_NAME=test \
  -e FLASK_SECRET_KEY=test \
  -e JWT_SECRET_KEY=test \
  -e JWT_ACCESS_TOKEN_EXPIRES=3600 \
  -e DB_USER=test \
  -e DB_PASSWORD=test \
  -e DB_HOST=test.rds.amazonaws.com \
  -e DB_PORT=5432 \
  -e DB_NAME=test \
  --entrypoint /bin/sh $IMAGE_NAME -c "
echo '=== Root directory (/var/task) ==='
ls -la /var/task/ | head -20
echo ''
echo '=== App directory (/var/task/app) ==='
ls -la /var/task/app/
echo ''
echo '=== Sample import test ==='
python -c 'import sys; print(\"Python path:\", sys.path[:3])'
python -c 'from app import create_app; print(\"✅ App import successful\")'
"

# Create test event
echo -e "${YELLOW}📝 Creating test event...${NC}"
cat > test-event.json << 'EOF'
{
  "httpMethod": "GET",
  "path": "/health",
  "headers": {
    "User-Agent": "Test/1.0",
    "Accept": "application/json"
  },
  "body": null,
  "isBase64Encoded": false
}
EOF

# Test the Lambda function
echo -e "${YELLOW}🚀 Testing Lambda function...${NC}"
docker run --rm \
  -e AWS_LAMBDA_FUNCTION_NAME=meal-planner-test \
  -e FLASK_SECRET_KEY=test-flask-secret \
  -e JWT_SECRET_KEY=test-jwt-secret \
  -e JWT_ACCESS_TOKEN_EXPIRES=3600 \
  -e DB_USER=testuser \
  -e DB_PASSWORD=testpass \
  -e DB_HOST=test-rds-proxy.proxy-abc123.us-east-1.rds.amazonaws.com \
  -e DB_PORT=5432 \
  -e DB_NAME=testdb \
  -e AWS_REGION=us-east-1 \
  -v $(pwd)/test-event.json:/tmp/test-event.json \
  --entrypoint /bin/sh $IMAGE_NAME -c '
python -c "
import json
import sys
sys.path.insert(0, '"'"'/var/task'"'"')
from wsgi_handler import handler

with open('"'"'/tmp/test-event.json'"'"') as f:
    event = json.load(f)
    
context = {}
response = handler(event, context)
print('"'"'\n✅ Lambda handler response:'"'"')
print(json.dumps(response, indent=2))

# Verify the response
if response.get('"'"'statusCode'"'"') == 200:
    body = json.loads(response.get('"'"'body'"'"', '"'"'{}'"'"'))
    if body.get('"'"'status'"'"') == '"'"'healthy'"'"':
        print('"'"'\n✅ Health check passed!'"'"')
    else:
        print('"'"'\n❌ Health check failed: unexpected response body'"'"')
        sys.exit(1)
else:
    status_code = response.get('"'"'statusCode'"'"')
    print('"'"'\n❌ Health check failed: status code'"'"', status_code)
    sys.exit(1)
"
'

# Clean up
echo -e "${YELLOW}🧹 Cleaning up...${NC}"
rm -rf $TEMP_DIR test-event.json
docker rmi $IMAGE_NAME 2>/dev/null || true

echo -e "${GREEN}✅ Local Lambda test complete!${NC}"
