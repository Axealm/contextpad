# ContextPad Terraform

This is an AWS infrastructure scaffold for the production version of ContextPad.

It intentionally avoids hardcoded secrets and destructive defaults. Before applying, choose the runtime mode:

- `lambda`: API Gateway + Lambda
- `ecs`: API Gateway or ALB + ECS Fargate

The initial MVP can be deployed as:

- S3 + CloudFront for the React app
- API Gateway + Lambda for the FastAPI app packaged as a container
- Cognito for authentication
- DynamoDB for low-cost serverless storage or RDS PostgreSQL for richer querying
- Bedrock for AI extraction
- Secrets Manager for Gmail OAuth credentials

## Commands

```bash
terraform init
terraform fmt
terraform validate
terraform plan
```
