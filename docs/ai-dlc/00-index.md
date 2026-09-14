# ContextPad AI-DLC Artifacts

Current implementation specifications in Japanese: [document index](../README.md).
The phase folders below are this project's organization of design evidence,
not proof that the official workflow runtime or all approval gates were run.

This folder captures the project lifecycle in an AI-DLC style. The goal is not to claim that AI replaces engineering judgment. The goal is to show that AI proposes, humans review, and implementation proceeds with explicit decisions.

## Inception

- `01-vision.md`
- `02-problem-statement.md`
- `03-personas.md`
- `04-user-stories.md`
- `05-requirements.md`

## Construction

- `06-architecture.md`
- `07-data-model.md`
- `08-api-design.md`
- `09-security-design.md`
- `10-adr.md`
- `11-test-strategy.md`
- `14-ui-design.md`
- `15-gmail-integration.md`

## Operations

- `13-release-operations.md`
- `16-free-development-roadmap.md`

## Governance

- `12-human-review-log.md`

## MVP Decision

The first implementation prioritizes a small but demonstrable work loop:

1. Paste or import an email summary.
2. Write a rough memo in natural Japanese.
3. Ask ContextPad to organize the context.
4. Review extracted tasks, people, schedule, place, and deadline.
5. Save the note as a structured work item.
