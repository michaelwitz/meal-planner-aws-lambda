#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🧪 Testing Lambda Endpoints Locally${NC}"
echo -e "${YELLOW}Note: Database endpoints will fail locally as they require AWS RDS Proxy${NC}\n"

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
PROJECT_ROOT="$(dirname "$BACKEND_DIR")"

# Change to project root
cd "$PROJECT_ROOT"

# Variables
TEMP_DIR="lambda-package-temp"
IMAGE_NAME="meal-planner-lambda-test"

# Build the package (reuse from test-lambda-local.sh)
echo -e "${YELLOW}📦 Building Lambda package...${NC}"
rm -rf $TEMP_DIR
mkdir -p $TEMP_DIR/app
cp -r backend/app/* $TEMP_DIR/app/
find $TEMP_DIR -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find $TEMP_DIR -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
find $TEMP_DIR -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
rm -f $TEMP_DIR/app/requirements.txt 2>/dev/null || true

# Create wsgi_handler.py
cat > $TEMP_DIR/wsgi_handler.py << 'EOF'
"""Lambda handler for Flask app."""
import serverless_wsgi
from app import create_app

app = create_app()

def handler(event, context):
    """Lambda handler function."""
    return serverless_wsgi.handle_request(app, event, context)
EOF

# Create requirements.txt
cat > $TEMP_DIR/requirements.txt << 'EOF'
Flask==3.0.0
Flask-Cors==6.0.0
Flask-JWT-Extended==4.5.3
Flask-SQLAlchemy==3.1.1
flask-pydantic==0.11.0
SQLAlchemy==2.0.23
psycopg2-binary==2.9.9
bcrypt==4.1.2
PyJWT==2.10.1
pydantic==2.5.2
pydantic-core==2.14.5
email-validator==2.1.0
python-dotenv==1.0.0
serverless-wsgi==3.0.3
Werkzeug==3.0.1
EOF

# Create Dockerfile
cat > $TEMP_DIR/Dockerfile << 'EOF'
FROM public.ecr.aws/lambda/python:3.11-arm64
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . /var/task/
CMD ["wsgi_handler.handler"]
EOF

# Build Docker image
docker build -q -t $IMAGE_NAME $TEMP_DIR

# Function to test an endpoint
test_endpoint() {
    local method=$1
    local path=$2
    local body=$3
    local description=$4
    local headers=$5
    
    echo -e "${BLUE}Testing: ${description}${NC}"
    echo -e "  ${method} ${path}"
    
    # Create event JSON
    cat > test-event.json << EOF
{
  "httpMethod": "${method}",
  "path": "${path}",
  "headers": {
    "User-Agent": "Test/1.0",
    "Accept": "application/json",
    "Content-Type": "application/json"
    ${headers}
  },
  "body": ${body},
  "isBase64Encoded": false
}
EOF
    
    # Run test
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
    
response = handler(event, {})
status = response.get('"'"'statusCode'"'"')
body = json.loads(response.get('"'"'body'"'"', '"'"'{}'"'"'))

if status == 200 or status == 201:
    print('"'"'  ✅ Status:'"'"', status)
    print('"'"'  Response:'"'"', json.dumps(body, indent=4))
else:
    print('"'"'  ❌ Status:'"'"', status)
    print('"'"'  Error:'"'"', json.dumps(body, indent=4))
" 2>/dev/null
'
    echo ""
}

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}1. BASIC ENDPOINTS (No Database Required)${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# Test health endpoint
test_endpoint "GET" "/health" "null" "Health Check"

# Test system info endpoint
test_endpoint "GET" "/test" "null" "System Info"

echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}2. DATABASE ENDPOINT (Will fail locally)${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# Test database endpoint
test_endpoint "GET" "/test-db" "null" "Database Connection Test"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}3. AUTH ENDPOINTS (Need DB for full test)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# Test registration endpoint (will fail due to DB)
test_endpoint "POST" "/api/auth/register" '"{\"email\":\"test@example.com\",\"username\":\"testuser\",\"password\":\"Test123!@#\",\"full_name\":\"Test User\",\"sex\":\"male\",\"phone_number\":\"+1234567890\",\"address_line_1\":\"123 Test St\",\"city\":\"Test City\",\"state_province_code\":\"TS\",\"country_code\":\"US\",\"postal_code\":\"12345\"}"' "User Registration"

# Clean up
rm -rf $TEMP_DIR test-event.json
docker rmi $IMAGE_NAME 2>/dev/null || true

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}📊 SUMMARY${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${GREEN}✅ What works locally:${NC}"
echo "  • Health check endpoint (/health)"
echo "  • System info endpoint (/test)"
echo "  • Lambda handler and Flask app initialization"
echo ""
echo -e "${YELLOW}⚠️  What needs AWS deployment to test:${NC}"
echo "  • Database connectivity (/test-db)"
echo "  • User registration (/api/auth/register)"
echo "  • User login (/api/auth/login)"
echo "  • Any endpoint requiring database access"
echo ""
echo -e "${BLUE}💡 To test database endpoints:${NC}"
echo "  1. Deploy to AWS Lambda: ./backend/scripts/deployment/deploy-lambda.sh"
echo "  2. Use API Gateway URL or AWS Console to test"
echo "  3. Check CloudWatch logs for debugging"
echo ""
echo -e "${YELLOW}🔧 Alternative for local DB testing:${NC}"
echo "  You could modify the config to use a local PostgreSQL"
echo "  container for development, but this won't test the"
echo "  RDS Proxy connection that Lambda uses in production."
