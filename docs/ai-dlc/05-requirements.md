# Requirements

Scope: target requirements, not an implementation-completion checklist.
Deletion, persistent storage, identity, and external integrations are not yet
implemented. See [current specification](../specification.md) for status.

## Functional Requirements

FR-01: Users can create, list, read, update, and delete work notes.

FR-02: A work note can store related email metadata:

- Gmail message ID
- Subject
- Sender
- Received time
- Snippet

FR-03: Users can enter rough memo text.

FR-04: The system extracts:

- Event date/time
- Location
- People
- Deadline
- Tasks
- Summary
- Confidence

FR-05: The system stores both raw input and structured output.

FR-06: The user can mark AI-extracted fields as reviewed.

FR-07: The system can search notes by text and structured fields.

FR-08: Gmail integration is designed through OAuth, but MVP can use pasted email data.

FR-09: Bedrock is the target AI provider, but MVP includes a deterministic local extractor for tests and offline demos.

## Non-Functional Requirements

NFR-01 Security: Email content must be treated as sensitive data.

NFR-02 Privacy: Users must explicitly connect Gmail and approve scopes.

NFR-03 Auditability: AI outputs and human review status must be persisted.

NFR-04 Reliability: API errors must be structured and user-readable.

NFR-05 Observability: Production workloads must emit logs, metrics, and alarms.

NFR-06 Cost: MVP should fit a low-cost AWS architecture.

NFR-07 Portability: The app should run locally without AWS credentials.

NFR-08 Maintainability: Design decisions must be captured as ADRs.

NFR-09 Testability: Extraction logic must have repeatable tests independent from live AI calls.

NFR-10 Accessibility: The UI must support keyboard navigation and readable contrast.
