# Lambda Deployment Guide

This guide provides comprehensive instructions for deploying the Flask Meal Planner application to AWS Lambda.

## Deployment Workflow

The deployment process is a two-step process that involves building a deployment package and then deploying it using the Serverless Framework.

### Step 1: Build the Deployment Package

Any time you make changes to the backend application, you must first build the deployment package. This includes changes to Python code in the `backend/app/` directory or dependencies in `backend/app/requirements.txt`.

To build the package, run the following command from the project root:

```bash
./build-package.sh
```

This script creates the `dist/lambda-package.zip` artifact, which is the deployment package for the Lambda function. We use the `dist` directory instead of `.serverless` because `.serverless` is a temporary directory that Serverless Framework manages and cleans up during deployment.

### Step 2: Deploy the Application

Once the deployment package has been built, you can deploy the application using the Serverless Framework. The following command will deploy the application to the `test` stage:

```bash
set -a; source .env; set +a; AWS_PROFILE=serverless-cli-user npx serverless deploy --stage test
```

This command will upload the `dist/lambda-package.zip` artifact to AWS Lambda and configure the necessary resources, such as API Gateway.

**Note:** The package is built in the `dist` directory rather than `.serverless` because `.serverless` is a temporary directory that Serverless Framework manages. Any files placed there may be cleaned up during the deployment process.

## Verifying the Deployment

Once the deployment is complete, you can verify it by checking the Lambda logs:

```bash
npx serverless logs -f app --stage test --tail
```

You can also test the deployed API endpoints using `curl` or a tool like Postman. The API endpoint URL can be found in the output of the `serverless deploy` command.
