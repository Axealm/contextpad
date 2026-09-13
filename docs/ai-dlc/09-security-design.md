# Security Design

Scope: target controls. The current local API has no authentication or
ownership enforcement; this document does not certify those controls exist.

## Data Classification

Email bodies, snippets, task contents, people names, and meeting locations are sensitive work data.

## Authentication

Target architecture uses Cognito Hosted UI. API Gateway validates JWTs before forwarding requests.

## Authorization

Every data object is scoped by `user_id`. The API must never accept a client-provided `user_id` as authority. It must derive user identity from the authenticated token.

## Gmail OAuth

MVP starts with pasted email metadata. Production Gmail integration should use:

- OAuth consent screen
- Least-privilege Gmail scopes
- Refresh tokens encrypted at rest
- Token storage in Secrets Manager or encrypted database columns
- Explicit disconnect flow

Proposed Gmail scope (restricted; review verification and assessment needs):

```text
https://www.googleapis.com/auth/gmail.readonly
```

Source: [Google Gmail scope documentation](https://developers.google.com/workspace/gmail/api/auth/scopes).

## Bedrock Data Handling

- Send only the email fields required for extraction.
- Do not log full prompts or raw email content in production.
- Validate Bedrock JSON responses before persistence.
- Store model ID and timestamp for auditability.

## Secrets

No secrets are committed to the repository. Use:

- Local `.env` files ignored by git
- AWS Secrets Manager in production
- GitHub Actions secrets for deployment credentials

## Logging

Safe to log:

- Request ID
- User ID hash
- Note ID
- Extraction duration
- Error code

Do not log:

- Email body
- OAuth tokens
- Raw Bedrock prompts
- Full extracted personal details
