# Release And Operations Design

Scope: cloud release proposal. Only the local demo and CI definitions exist.
Preview/production deployments, alarms, backups, and cloud runbooks have not
been exercised. See [current operations guide](../test-and-operations.md).

## Environments

- Local: developer machine, deterministic extractor
- Preview: deployed from pull request branch
- Production: main branch deployment

## Release Flow

1. AI or human proposes a change.
2. Human reviews requirements, code, and tests.
3. CI runs lint, type checks, API tests, and frontend build.
4. Terraform plan is reviewed.
5. Deployment proceeds after approval.
6. CloudWatch dashboards and alarms are checked.

## GitHub Actions

CI should run:

- Python tests
- Frontend type check and build
- Terraform fmt check

Deployment should require:

- AWS credentials through GitHub OIDC
- Environment approval for production

## Monitoring

CloudWatch metrics:

- API latency
- API 4xx and 5xx rate
- Extraction latency
- Bedrock failure count
- Gmail API failure count

Alarms:

- 5xx rate above threshold
- Bedrock failures above threshold
- API latency regression

## Runbook: Bedrock Extraction Fails

1. Check CloudWatch error logs by request ID.
2. Confirm Bedrock model access and quota.
3. Check schema validation failure count.
4. Fall back to deterministic extractor if configured.
5. Record incident notes and update tests if a new malformed output pattern appears.

## Runbook: Gmail OAuth Fails

1. Confirm user consent status.
2. Check token refresh error code.
3. Ask user to reconnect Gmail if refresh token is invalid.
4. Verify OAuth client secret in Secrets Manager.

## Backup And Retention

- Database backups enabled in production.
- OAuth tokens deleted immediately on account disconnect.
- User note deletion should delete linked extracted context and review events.
