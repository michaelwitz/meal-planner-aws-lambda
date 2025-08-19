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
- AWS CLI configured
- [uv](https://github.com/astral-sh/uv) for fast package management

### Setup

1. **Clone and setup environment:**
```bash
git clone <repo-url>
cd meal-planner-aws-lambda

# Setup Python environment
uv venv --python 3.11
source .venv/bin/activate

# Install dependencies
uv pip install -r backend/requirements.txt
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
python scripts/rebuild_db.py --local
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
python -m app
# API available at http://localhost:5000
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
export USE_LOCAL_DB=false
cd backend
python -m app
```

This allows you to:
- Test with real cloud infrastructure before deploying
- Debug issues with actual AWS services
- Validate RDS Serverless scaling behavior
- Ensure your code works with cloud-specific features

## Documentation

- [Implementation Plan](docs/ImplementationPlan.md) - Detailed AWS setup instructions
- [WARP.md](WARP.md) - Development commands and tips (not in git)

## Project Status

- ✅ Phase 1: Authentication (In Progress)
- 📋 Phase 2: Food Catalog (Planned)
- 📋 Phase 3: Meal Planning (Planned)
- 📋 Phase 4: Frontend (Future)

## License

[Your License]
