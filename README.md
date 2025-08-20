# Meal Planner AWS Lambda

A cloud-native meal planning application using AWS Lambda, RDS Serverless PostgreSQL, and Flask.

## ⚠️ Python Version Requirement

**This project requires Python 3.11.x** (not 3.12 or higher)

## Database Connection Options

This project supports three database configurations:

### 1. **Local PostgreSQL (Docker)** - For offline development
- Fast, no internet required
- Data persists in Docker volumes
- Perfect for initial development and testing

### 2. **Cloud RDS Serverless (Direct)** - For integration testing
- Connect directly from local Python to AWS RDS Serverless v2
- Your IP must be whitelisted in RDS security group
- Uses the actual cloud database
- Good for testing before Lambda deployment

### 3. **Lambda with RDS Proxy** - Production
- Lambda functions connect through RDS Proxy
- Connection pooling managed by proxy
- No connection exhaustion issues

## Quick Start

### Prerequisites

- Python 3.11.x (required)
- Docker & Docker Compose (for local PostgreSQL)
- AWS CLI configured (for cloud deployment)
- [uv](https://github.com/astral-sh/uv) for Python package management
- Serverless Framework v3.40.0 - [See setup guide](docs/Serverless-Setup.md)

### Setup

1. **Clone and setup environment:**
```bash
git clone <repo-url>
cd meal-planner-aws-lambda

# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh
# Or with Homebrew: brew install uv

# Setup Python environment with uv
uv venv
source .venv/bin/activate

# Install dependencies with uv
uv pip install -r backend/app/requirements.txt
```

2. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your settings
```

3. **Choose your database:**

**Option A: Local PostgreSQL (Recommended for development)**
```bash
# Start local database
docker-compose up -d

# Initialize database
cd backend
export USE_LOCAL_DB=true
python scripts/rebuild_db.py
```

**Option B: Cloud RDS Serverless**
```bash
# First, create AWS infrastructure (see docs/ImplementationPlan.md)
# Then initialize cloud database
cd backend
export USE_LOCAL_DB=false
python scripts/rebuild_db.py
```

4. **Run the application:**
```bash
cd backend
./start-dev-server.sh
# Or manually:
export USE_LOCAL_DB=true
python -m app
# API available at http://localhost:5050
# Note: Port 5050 avoids conflict with macOS AirPlay
```

## Database Connection Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Development Phase                      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Local Python ──────► Local PostgreSQL (Docker)         │
│       │                                                  │
│       └──────────────► Cloud RDS Serverless (Direct)    │
│                                                          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                   Production Phase                       │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  API Gateway ──► Lambda ──► RDS Proxy ──► RDS Serverless│
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Key Features

- **Flexible Database Connections**: Seamlessly switch between local and cloud databases
- **Blueprint Architecture**: Same structure as meal-planner-docker for code reuse
- **RDS Serverless v2**: Auto-scaling database (0.5-2 ACU)
- **JWT Authentication**: Secure token-based auth
- **Monorepo Structure**: Backend and frontend in same repository

## Testing Cloud Database from Local

Yes, you can absolutely connect to RDS Serverless from your local Python! 

```bash
# Ensure your IP is whitelisted
export MY_IP=$(curl -s https://checkip.amazonaws.com)
aws ec2 authorize-security-group-ingress \
  --group-id $RDS_SECURITY_GROUP_ID \
  --protocol tcp \
  --port 5432 \
  --cidr ${MY_IP}/32

# Run locally against cloud database
cd backend
source ../.venv/bin/activate
export USE_LOCAL_DB=false
python -m app
```

This allows you to:
- Test with real cloud infrastructure before deploying
- Debug issues with actual AWS services
- Validate RDS Serverless scaling behavior
- Ensure your code works with cloud-specific features

## Documentation

- [Implementation Guide](docs/ImplementationGuide.md) - Detailed AWS setup instructions and IAM policies.
- [Serverless Setup](docs/Serverless-Setup.md) - Serverless Framework v3 installation and configuration
- [Lambda-RDS Connection](docs/Lambda-RDS-Connection.md) - Database connection architecture
- [RDS Setup](docs/RDS-Setup.md) - RDS Serverless v2 configuration
- [WARP.md](WARP.md) - Development commands and tips (not in git)

## Deployment

For detailed deployment instructions, please see the [Lambda Deployment Guide](docs/Lambda-Deployment.md).

## Project Status (2025-08-20)

### ✅ Working Features:
- **Local Development**: Flask app runs successfully with both Docker PostgreSQL and cloud RDS
- **Cloud Database**: RDS Serverless v2 PostgreSQL deployed, seeded, and tested
- **Authentication API**: All auth endpoints (register, login, profile) working locally
- **RDS Proxy**: Configured for Lambda connection pooling
- **Lambda Deployment**: Successfully deployed to AWS using Serverless Framework v3.40.0

### ⚠️ Known Issues:
- **Lambda Endpoint Timeout**: Deployed Lambda function times out when accessing API endpoints. This appears to be a network connectivity issue between Lambda and RDS Proxy that needs debugging.

### 📋 Roadmap:
- ✅ Phase 1A: Local Development with Authentication (Complete)
- ✅ Phase 1B: Cloud RDS Integration (Complete)
- 🔧 Phase 1C: Lambda Deployment (In Progress - debugging timeout issue)
- 📋 Phase 2: Food Catalog (Planned)
- 📋 Phase 3: Meal Planning (Planned)
- 📋 Phase 4: Frontend (Future)

## License

[Your License]
