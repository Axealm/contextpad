# Architecture Decision Records

## ADR-001: Use React and FastAPI for MVP

Status: Requested technology stack; implemented locally. Design review pending.

Context: The portfolio should demonstrate TypeScript frontend and Python backend skills.

Decision: Use React/TypeScript for the web app and Python/FastAPI for the API.

Consequences:

- Fast iteration locally
- Clear API contract
- Direct migration path to Lambda container or ECS Fargate

## ADR-002: Keep Local Extractor Alongside Bedrock Interface

Status: Implemented as a local prototype choice; human acceptance pending.

Context: Bedrock calls require AWS credentials and may cost money.

Decision: Implement deterministic extraction for tests and local demos, behind the same service boundary as Bedrock.

Consequences:

- Offline demo works
- Tests are stable
- Bedrock can be added without changing API shapes

## ADR-003: Start With Pasted Gmail Metadata

Status: Implemented as a local prototype choice; human acceptance pending.

Context: Gmail OAuth adds setup complexity and review requirements.

Decision: MVP supports pasted email metadata first. Gmail API integration is designed but deferred.

Update (2026-09-14): Gmail deferral is superseded by ADR-005 after the user
explicitly prioritized Gmail. Manual entry remains available. Real-account
configuration and verification are still pending.

Consequences:

- Product loop can be tested earlier
- OAuth security design is still documented
- Later Gmail integration has a clear boundary

## ADR-004: Prefer PostgreSQL For Full Version, Keep DynamoDB Option

Status: Proposed

Context: Notes, reviews, and email links are relational, but serverless cost matters.

Decision: Use repository abstraction. Production can choose PostgreSQL on RDS or DynamoDB depending on cost and query needs.

Consequences:

- PostgreSQL improves search and audit queries
- DynamoDB lowers operations burden
- Repository boundary prevents storage choice from leaking into handlers

## ADR-005: Local Readonly Gmail Integration

Status: Gmail priority requested; implemented locally with mocked verification.
Detailed human acceptance and live Google connection remain pending.

See [Gmail integration design](15-gmail-integration.md) for the alternatives,
security boundary, temporary storage tradeoff, and rollout conditions.
