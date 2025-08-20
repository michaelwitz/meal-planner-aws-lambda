# Lambda Troubleshooting Guide

## Current Issue: Lambda Endpoint Timeout (2025-08-20)

### Problem Description
After successfully deploying the Flask application to AWS Lambda using Serverless Framework v3.40.0, the deployed API endpoints are timing out when accessed via curl.

**Test Command:**
```bash
curl -X POST https://c557ywae4j.execute-api.us-east-1.amazonaws.com/test/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser_lambda", "email": "testuser_lambda@example.com", "password": "Test123!"}'
```

**Result:** The request hangs and eventually times out (or is interrupted with Ctrl+C).

### Deployment Details
- **Stage:** test
- **Endpoint:** `https://c557ywae4j.execute-api.us-east-1.amazonaws.com/test/`
- **Function:** meal-planner-test-app (103 kB)
- **Runtime:** Python 3.11
- **Environment Variables:** All properly loaded via serverless-dotenv-plugin
- **VPC Configuration:** Lambda is in VPC with security groups configured

### What's Working
✅ Local Flask app runs successfully  
✅ Local app connects to cloud RDS database directly  
✅ All pytest tests pass against cloud database  
✅ Lambda deployment succeeds without errors  
✅ Environment variables are properly configured  
✅ RDS Proxy is created and configured  

### What's Not Working
❌ Lambda function times out when accessing any endpoint  
❌ No clear error messages in initial attempts  

## Debugging Steps

### 1. Check CloudWatch Logs
```bash
# View Lambda function logs
aws logs tail /aws/lambda/meal-planner-test-app --follow

# Or using Serverless Framework
npx serverless logs -f app --stage test --tail
```

Look for:
- Connection timeout errors
- Database connection failures
- Python exceptions
- VPC/Network errors

### 2. Verify Security Groups

#### Check Lambda Security Group
```bash
source .env
aws ec2 describe-security-groups --group-ids $LAMBDA_SECURITY_GROUP_ID
```

Ensure Lambda security group has:
- Outbound rule allowing traffic to RDS Proxy security group on port 5432
- Outbound rule allowing HTTPS (443) for AWS service calls

#### Check RDS Security Group
```bash
aws ec2 describe-security-groups --group-ids $RDS_SECURITY_GROUP_ID
```

Ensure RDS security group has:
- Inbound rule from Lambda security group on port 5432
- Inbound rule from RDS Proxy security group (if different)

### 3. Test RDS Proxy Connection

#### Check RDS Proxy Status
```bash
aws rds describe-db-proxies --db-proxy-name meal-planner-proxy
```

Look for:
- Status should be "available"
- VPC subnet IDs should match Lambda's VPC configuration
- Security groups should allow Lambda access

#### Check RDS Proxy Targets
```bash
aws rds describe-db-proxy-targets --db-proxy-name meal-planner-proxy
```

Ensure:
- Target health is "AVAILABLE"
- Connection pool is not exhausted

### 4. Verify Lambda VPC Configuration

```bash
# Get Lambda function configuration
aws lambda get-function-configuration --function-name meal-planner-test-app
```

Check:
- VpcConfig includes correct subnet IDs
- SecurityGroupIds includes the Lambda security group
- Environment variables include RDS_PROXY_ENDPOINT

### 5. Test Database Connection in Lambda

Create a simple test Lambda function to isolate database connectivity:

```python
import os
import json
import psycopg2

def test_db_connection(event, context):
    try:
        conn = psycopg2.connect(
            host=os.environ['RDS_PROXY_ENDPOINT'],
            database=os.environ['DB_NAME'],
            user=os.environ['DB_USER'],
            password=os.environ['DB_PASSWORD'],
            port=5432,
            connect_timeout=5
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        result = cursor.fetchone()
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'db_version': result[0]
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }
```

Deploy and test this separately to isolate the issue.

## Common Lambda-RDS Issues and Solutions

### Issue 1: Lambda Cannot Reach RDS Proxy
**Symptoms:** Connection timeout errors in CloudWatch logs

**Solutions:**
1. Ensure Lambda and RDS Proxy are in the same VPC
2. Check security group rules allow traffic between them
3. Verify subnet routing tables

### Issue 2: RDS Proxy Authentication Failure
**Symptoms:** Authentication errors in logs

**Solutions:**
1. Verify Secrets Manager secret contains correct credentials
2. Check IAM role allows Lambda to read the secret
3. Ensure RDS Proxy is configured to use the correct secret

### Issue 3: Lambda Cold Start Timeout
**Symptoms:** First request times out, subsequent requests work

**Solutions:**
1. Increase Lambda timeout (currently 30 seconds)
2. Implement connection retry logic
3. Use provisioned concurrency for critical endpoints

### Issue 4: Missing Environment Variables
**Symptoms:** KeyError or undefined variable errors

**Solutions:**
1. Verify all required environment variables are in serverless.yml
2. Check .env file is loaded before deployment
3. Export variables in shell before running serverless deploy:
   ```bash
   set -a; source .env; set +a
   npx serverless deploy --stage test
   ```

### Issue 5: VPC Configuration Issues
**Symptoms:** Lambda cannot access internet or AWS services

**Solutions:**
1. If Lambda needs internet access, ensure VPC has NAT Gateway
2. For AWS service access only, use VPC endpoints
3. Check route tables for proper configuration

## Next Debugging Steps (To Do)

1. **Check CloudWatch Logs**
   ```bash
   aws logs tail /aws/lambda/meal-planner-test-app --follow
   ```

2. **Verify Security Group Rules**
   ```bash
   # Check if Lambda SG can reach RDS Proxy
   aws ec2 describe-security-groups --group-ids $LAMBDA_SECURITY_GROUP_ID --query 'SecurityGroups[0].IpPermissionsEgress'
   ```

3. **Test with Increased Timeout**
   Update serverless.yml:
   ```yaml
   functions:
     app:
       handler: wsgi_handler.handler
       timeout: 60  # Increase from 30 to 60 seconds
   ```

4. **Add Debug Logging**
   Update backend/app/config.py to add more logging:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   logger = logging.getLogger(__name__)
   
   # Log database connection attempts
   logger.debug(f"Attempting to connect to: {db_host}")
   ```

5. **Create Minimal Test Endpoint**
   Add a simple endpoint that doesn't require database:
   ```python
   @app.route('/test')
   def test():
       return {'status': 'ok', 'timestamp': datetime.now().isoformat()}
   ```

## Recovery Plan

If the timeout issue cannot be resolved quickly:

1. **Fall back to local development** with cloud RDS (currently working)
2. **Consider alternative deployment options:**
   - ECS Fargate (more traditional containerized approach)
   - EC2 with auto-scaling group
   - Direct Lambda invocation without API Gateway
3. **Investigate RDS Data API** as alternative to traditional connections

## Resources

- [AWS Lambda VPC Networking](https://docs.aws.amazon.com/lambda/latest/dg/configuration-vpc.html)
- [RDS Proxy with Lambda](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/rds-proxy-lambda.html)
- [Serverless Framework Debugging](https://www.serverless.com/framework/docs/providers/aws/guide/debugging)
- [Lambda CloudWatch Insights](https://docs.aws.amazon.com/lambda/latest/dg/monitoring-insights.html)
