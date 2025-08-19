# TODO - AWS Lambda Meal Planner

## Documentation Tasks

### AWS IAM Policies
- [ ] Document the IAM policies required for `serverless-cli-user` profile
  - [ ] EC2 permissions (VPC, Security Groups, Subnets)
  - [ ] RDS permissions (Create/manage clusters, subnet groups)
  - [ ] Lambda deployment permissions
  - [ ] API Gateway permissions
  - [ ] CloudFormation permissions (for Serverless Framework)
  - [ ] IAM role creation (for Lambda execution)
  - [ ] Secrets Manager permissions (if using)
  - [ ] CloudWatch Logs permissions

### Deployment Documentation
- [ ] Create `docs/AWS-IAM-Setup.md` with:
  - Complete IAM policy JSON for the serverless-cli-user
  - Step-by-step guide to create the IAM user
  - How to configure AWS CLI profile
  - Minimum required permissions vs. recommended permissions

- [ ] Update `docs/Serverless-Deployment.md` with:
  - IAM requirements for Serverless Framework
  - How to configure serverless.yml with the profile
  - Environment variables needed for Lambda
  - VPC configuration for Lambda to access RDS

### Infrastructure Documentation
- [ ] Document RDS Proxy setup (when implemented)
- [ ] Document Lambda cold start optimization strategies
- [ ] Add troubleshooting guide for common AWS permission errors

## Development Tasks

### Backend
- [ ] Implement remaining API endpoints (foods, meals)
- [ ] Add API documentation (OpenAPI/Swagger)
- [ ] Implement proper error handling for Lambda
- [ ] Add request validation middleware
- [ ] Implement rate limiting

### AWS Lambda
- [ ] Configure Lambda handlers in `backend/app/handlers/`
- [ ] Set up proper Lambda layers for dependencies
- [ ] Configure environment variables in serverless.yml
- [ ] Implement connection pooling for RDS
- [ ] Add Lambda warmup strategy

### Database
- [ ] Set up RDS Proxy for production Lambda connections
- [ ] Implement database migrations strategy
- [ ] Add database backup automation
- [ ] Document disaster recovery procedures

### Security
- [ ] Implement API key authentication for public endpoints
- [ ] Add request signing/verification
- [ ] Implement proper CORS configuration
- [ ] Add input sanitization
- [ ] Security audit of all endpoints

### Testing
- [ ] Add unit tests for all endpoints
- [ ] Add integration tests for Lambda handlers
- [ ] Set up CI/CD pipeline
- [ ] Add load testing scripts
- [ ] Test Lambda cold starts and timeouts

### Frontend (Future)
- [ ] Set up React project structure
- [ ] Configure build pipeline for S3/CloudFront
- [ ] Implement authentication flow
- [ ] Create meal planning UI

## Notes

### Current Profile Requirements
The `serverless-cli-user` AWS profile currently needs permissions for:
1. **RDS operations** - Creating and managing Aurora Serverless v2
2. **EC2 operations** - Managing VPCs, security groups, subnets
3. **Future Lambda/Serverless** - Will need CloudFormation, Lambda, API Gateway, IAM roles

### Cost Optimization
- RDS configured with 0 ACU minimum (auto-pauses after ~15 min)
- Remember to document wake-up time (15-30 seconds) in user guides
- Consider implementing a "wake up" endpoint for better UX

---
*Last Updated: 2024-01-19*
