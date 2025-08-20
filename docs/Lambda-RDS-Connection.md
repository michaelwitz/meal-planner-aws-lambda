# Lambda to RDS Serverless v2 Connection Guide

This guide explains how the AWS Lambda function connects to the RDS Serverless v2 PostgreSQL database via the RDS Proxy. This setup is critical for production environments to manage database connections efficiently and prevent connection exhaustion.

## Architecture

The current architecture uses the RDS Proxy as an intermediary between the Lambda function and the RDS Serverless v2 database. This provides a pool of warm database connections, which is essential for handling the ephemeral nature of Lambda functions.

```
┌─────────────────┐      ┌─────────────────┐      ┌──────────────────────┐
│  Lambda Function  │─────▶│    RDS Proxy    │─────▶│  RDS Serverless v2   │
└─────────────────┘      └─────────────────┘      └──────────────────────┘
```

## RDS Proxy Configuration

The `meal-planner-proxy` is configured with the following key settings:

*   **Engine Family**: `POSTGRESQL`
*   **Authentication**: Uses AWS Secrets Manager to securely store and provide database credentials to the proxy.
*   **VPC**: The proxy is located in the same VPC as the Lambda function and the RDS database, ensuring secure and low-latency communication.
*   **Endpoint**: The Lambda function connects to the proxy using its unique endpoint: `meal-planner-proxy.proxy-cczg0cscuj55.us-east-1.rds.amazonaws.com`
*   **TLS**: TLS is required for all connections to the proxy, ensuring data is encrypted in transit.

### Setting up the RDS Proxy

To create and configure the RDS Proxy, you can use the AWS CLI. The following command provides an example of how to create the proxy:

```bash
aws rds create-db-proxy \
    --db-proxy-name meal-planner-proxy \
    --engine-family POSTGRESQL \
    --role-arn arn:aws:iam::512662829295:role/rds-proxy-role-meal-planner \
    --vpc-subnet-ids "subnet-0aea07bbb011a0bab,subnet-054c26c1e75b269e1" \
    --vpc-security-group-ids "sg-0fd605efde80bd711" \
    --auth "AuthScheme=SECRETS,SecretArn=arn:aws:secretsmanager:us-east-1:512662829295:secret:rds-proxy-secret-meal-planner-7Ps2c0,IAMAuth=DISABLED" \
    --require-tls
```

## Lambda Function Configuration

The `meal-planner-test-app` Lambda function is configured to connect to the RDS Proxy. The following settings are essential for this connection:

*   **VPC**: The Lambda function is in the same VPC as the RDS Proxy and the database.
*   **Security Groups**: The function's security group is configured to allow outbound traffic to the RDS Proxy's security group on port 5432.
*   **Environment Variables**: The `DB_HOST` environment variable is set to the RDS Proxy endpoint. This directs the application to connect to the proxy instead of directly to the database.

### Security Group Configuration

A critical part of the configuration is the security group rule that allows the Lambda function to communicate with the RDS Proxy. The Lambda function and the RDS Proxy share the same security group, so you need to add an ingress rule that allows traffic on port 5432 from the security group to itself.

```bash
aws ec2 authorize-security-group-ingress \
    --group-id sg-0fd605efde80bd711 \
    --protocol tcp \
    --port 5432 \
    --source-group sg-0fd605efde80bd711
```

### Verifying the Configuration

You can use the AWS CLI to verify the Lambda function's configuration:

```bash
aws lambda get-function-configuration --function-name meal-planner-test-app --region us-east-1
```

This will return a JSON object containing the function's configuration, including the VPC settings and environment variables. You should see that the `DB_HOST` environment variable is set to the RDS Proxy endpoint.

## Security Best Practices

*   **IAM Roles**: Use IAM roles with the principle of least privilege to control access to the RDS Proxy and the database.
*   **Secrets Manager**: Store all database credentials in AWS Secrets Manager and use the RDS Proxy's authentication feature to securely provide them to the proxy.
*   **TLS**: Always require TLS for connections to the RDS Proxy to ensure data is encrypted in transit.
