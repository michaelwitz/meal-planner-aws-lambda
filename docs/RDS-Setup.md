# RDS Serverless v2 Setup and Connection Guide

This guide explains how to set up and connect to the AWS RDS Serverless v2 PostgreSQL database across all defined environments.

## Environment Connection Architecture

This project defines four distinct environments, each with a specific database connection strategy. The application automatically switches between them based on environment variables.

| Environment | Application Host | Database Host | Connection Method |
| :--- | :--- | :--- | :--- |
| **`dev-local`** | Local Laptop | Local Docker | Direct Connection |
| **`dev-cloud`** | Local Laptop | AWS RDS | Direct Connection |
| **`test`** | AWS Lambda (test) | AWS RDS | via RDS Proxy |
| **`production`** | AWS Lambda (prod) | AWS RDS | via RDS Proxy |

```
                                  ┌───────────────────────────┐
                                  │    AWS RDS Serverless v2  │
                                  │      (PostgreSQL)         │
                                  └─────────────┬─────────────┘
                                                │
                           ┌────────────────────┼────────────────────┐
                           │                    │                    │
┌──────────────────┐     ┌─┴────────────────┐ ┌─┴────────────────┐ ┌─┴────────────────┐
│ Local PostgreSQL │◀───▶│  dev-cloud       │ │  test Stage        │ │ production Stage   │
│    (Docker)      │     │ (Local Laptop)   │ │  (AWS Lambda)      │ │ (AWS Lambda)       │
└──────────────────┘     └──────────────────┘ └───────┬──────────┘ └───────┬──────────┘
                                                      │                    │
                                                      └───────┬────────────┘
                                                              │
                                                          ┌───┴───┐
                                                          │  RDS  │
                                                          │ Proxy │
                                                          └───────┘
```

## How the Application Switches Connections

The logic in `backend/app/config.py` automatically selects the correct database configuration:

1.  **Lambda vs. Local**: It first checks for the `AWS_LAMBDA_FUNCTION_NAME` environment variable.
    *   If **present**, it activates the `test` or `production` configuration, which connects via the **RDS Proxy**. The proxy endpoint is specified in the `DB_HOST` environment variable within `serverless.yml`.
    *   If **absent**, it knows it's running on a local machine.
2.  **Local DB vs. Cloud DB**: For local execution, it checks the `USE_LOCAL_DB` variable in your `.env` file.
    *   If `true`, it activates the **`dev-local`** configuration, connecting to a local Docker PostgreSQL instance using the `LOCAL_DB_*` variables.
    *   If `false`, it activates the **`dev-cloud`** configuration, connecting directly to the RDS cluster endpoint using the `DB_HOST` variable.

## Environment Configuration (.env)

To work with the `dev-local` and `dev-cloud` environments, your `.env` file must be configured correctly. The `test` and `production` environments are configured via `serverless.yml`.

```bash
# dev-cloud: Direct connection to the AWS RDS instance
# To use this, set USE_LOCAL_DB=false in this file or your shell.
DB_HOST=<your-rds-cluster-endpoint> # Do not use the proxy endpoint here
DB_PORT=5432
DB_NAME=meal_planner
DB_USER=meal_planner_admin
DB_PASSWORD=<your-secure-password>

# dev-local: Connection to a local PostgreSQL instance running in Docker
# To use this, set USE_LOCAL_DB=true in this file or your shell.
USE_LOCAL_DB=true
LOCAL_DB_HOST=localhost
LOCAL_DB_PORT=5432
LOCAL_DB_USER=postgres
LOCAL_DB_PASSWORD=postgres
LOCAL_DB_NAME=mealplanner_dev
```

## Initial AWS RDS Setup

The `scripts/setup-rds-serverless.sh` script automates the creation of the RDS Serverless v2 instance. This only needs to be run once.

**Important**: This script uses the `serverless-cli-user` AWS profile, which is hardcoded in the script. Before running, ensure that this profile is correctly configured in your AWS credentials file (`~/.aws/credentials`).

```bash
# Make the script executable
chmod +x scripts/setup-rds-serverless.sh

# Run the setup
./scripts/setup-rds-serverless.sh
```

This script provisions the RDS cluster and the security group needed for both direct (`dev-cloud`) and proxy (`test`/`production`) access. After it runs, be sure to update your `.env` file with the output.

## Managing Access for dev-cloud

For the direct `dev-cloud` connection to work, your local IP address must be authorized in the RDS security group. If your IP address changes, you must update the rule.

```bash
# Get your new IP
export MY_IP=$(curl -s https://checkip.amazonaws.com)

# Update security group ingress rule
aws ec2 authorize-security-group-ingress \
  --group-id $RDS_SECURITY_GROUP_ID \
  --protocol tcp \
  --port 5432 \
  --cidr ${MY_IP}/32
```
