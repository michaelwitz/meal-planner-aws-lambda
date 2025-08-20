# Serverless Framework Setup

## Serverless Framework and Deployment

The Serverless Framework is used to define and deploy all the necessary AWS infrastructure for this project, including:

*   The Lambda function itself
*   API Gateway endpoints
*   VPC, subnets, and security groups
*   IAM roles and permissions
*   Environment variables

### The Deployment Process

While the Serverless Framework defines the infrastructure, the deployment process is a two-step process that uses a custom build script in conjunction with the Serverless Framework.

1.  **Build the Deployment Package**: The `build-package.sh` script is used to create the deployment artifact. This script correctly packages the Flask application and its dependencies into a zip file that is ready for deployment.
2.  **Deploy with Serverless**: The `serverless deploy` command is used to deploy the package created by the build script. The `serverless.yml` file is configured to use the artifact created by the `build-package.sh` script, so the `serverless deploy` command will automatically deploy the correct package.

This hybrid approach gives us the best of both worlds: the power of the Serverless Framework for infrastructure management, and the flexibility of a custom build script for packaging our application.

## Why Serverless Framework v3.40.0?

This project uses **Serverless Framework v3.40.0** (released April 2024), which is the final v3 release.

### Version Choice Rationale

| Version | Release Date | License/Cost | Authentication | Our Choice |
|---------|-------------|--------------|----------------|------------|
| v3.40.0 | April 2024 | Open Source (MIT) | None required | ✅ **Selected** |
| v4.0+ | May 2024+ | Freemium | Account/License required | ❌ Not used |

**Key Reasons:**
- **No authentication required** - v3 is fully open source
- **No account registration** - Deploy directly to AWS
- **Feature complete** - Has all features needed for Lambda deployment
- **Stable** - Final v3 release with 8+ months of production use
- **Free forever** - MIT licensed, no future licensing concerns

## Installation

```bash
# Install Serverless Framework v3 globally
npm install -g serverless@3

# Verify installation (should show Framework Core: 3.40.0)
serverless --version

# Expected output:
# Framework Core: 3.40.0
# Plugin: 7.2.3
# SDK: 4.5.1
```

## Required Plugins

Install these plugins in your project root:

```bash
# Initialize package.json if not exists
npm init -y

# Install serverless plugins for Python/Flask
npm install --save-dev \
  serverless-wsgi \
  serverless-python-requirements \
  serverless-dotenv-plugin \
  serverless-offline

# Note: Use --legacy-peer-deps if you encounter dependency conflicts
npm install --save-dev serverless-wsgi serverless-python-requirements serverless-dotenv-plugin serverless-offline --legacy-peer-deps
```

## Plugin Descriptions

- **serverless-wsgi**: Wraps Flask/WSGI apps for Lambda
- **serverless-python-requirements**: Handles Python dependencies and Lambda layers
- **serverless-dotenv-plugin**: Loads environment variables from .env files
- **serverless-offline**: Local Lambda simulation for testing

## AWS Credentials Setup

Serverless v3 uses AWS CLI credentials:

```bash
# Verify AWS credentials are configured
aws sts get-caller-identity

# Set AWS profile for Serverless
export AWS_PROFILE=serverless-cli-user

# Or configure in serverless.yml:
# provider:
#   profile: serverless-cli-user
```

## Deployment Commands

### Deployment

```bash
# Build the deployment package
./build-package.sh

# Deploy the package
set -a; source .env; set +a; AWS_PROFILE=serverless-cli-user npx serverless deploy --stage test
```

**Note**: Always use `test` or `production` as stage names, not `dev`.

## Migration Notes

### If upgrading from v4 to v3

```bash
# Uninstall v4
npm uninstall -g serverless

# Install v3
npm install -g serverless@3

# No dashboard login needed for v3!
```

### If considering v4 in the future

v4 requires one of:
- Free account at app.serverless.com (with usage limits)
- Paid license for commercial use > $2M revenue
- Self-hosted dashboard (Enterprise)

For open source projects or those wanting to avoid vendor lock-in, v3.40.0 remains the recommended choice.

## Troubleshooting

### Issue: "Serverless Framework V4 CLI requires an account"
**Solution**: You have v4 installed. Downgrade to v3:
```bash
npm uninstall -g serverless
npm install -g serverless@3
```

### Issue: Plugin version conflicts
**Solution**: Use legacy peer deps:
```bash
npm install --legacy-peer-deps
```

### Issue: "Cannot find module 'serverless-wsgi'"
**Solution**: Install plugins locally in project:
```bash
cd /path/to/project
npm install --save-dev serverless-wsgi
```

## References

- [Serverless Framework v3 Documentation](https://v3.serverless.com/framework/docs)
- [v3.40.0 Release Notes](https://github.com/serverless/serverless/releases/tag/v3.40.0)
- [v3 vs v4 Comparison](https://www.serverless.com/framework/docs/guides/upgrading-v4)
