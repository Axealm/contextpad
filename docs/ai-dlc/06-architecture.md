# Architecture

## MVP Architecture

```text
React / TypeScript
        |
        v
FastAPI
        |
        +-- Local deterministic extractor
        +-- Bedrock extractor interface
        +-- In-memory repository for local demo
```

The MVP keeps runtime simple so the product loop is demonstrable without AWS credentials.

## Target AWS Architecture

```text
User
 |
 v
CloudFront
 |
 +-- S3 static web app
 |
 v
API Gateway
 |
 v
Lambda or ECS Fargate
 |
 +-- Cognito authorizer
 +-- RDS PostgreSQL or DynamoDB
 +-- Secrets Manager for Gmail OAuth secrets
 +-- Bedrock for AI extraction
 +-- CloudWatch logs, metrics, alarms
```

## Service Choices

- Frontend: React + TypeScript
- API: Python + FastAPI
- Auth: Cognito Hosted UI
- Email: Gmail API with OAuth
- AI: Amazon Bedrock
- Storage: PostgreSQL for relational audit/history, DynamoDB as lower-cost MVP alternative
- Static hosting: S3 + CloudFront
- Secrets: AWS Secrets Manager
- Infrastructure: Terraform
- CI/CD: GitHub Actions

## Target Runtime Flow (Not Connected)

1. User signs in through Cognito.
2. User connects Gmail through OAuth.
3. User selects or pastes an email.
4. User writes rough memo.
5. API sends normalized input to extraction service.
6. Bedrock returns structured JSON.
7. API validates and stores extracted fields.
8. User reviews and confirms fields.

## Local Demo Flow

1. User opens the React app.
2. User enters sample email metadata and memo.
3. API runs deterministic extraction.
4. UI displays structured context.
