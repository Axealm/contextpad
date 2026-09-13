# Human Review Log

This file records the AI-DLC approval trail. The reviewer should update status before treating AI output as accepted.

## Review 001: Initial Product Direction

Date: 2026-09-13

AI proposal:

- Build ContextPad as a work memo linked to email.
- Use AI to extract dates, places, people, deadlines, and tasks.
- Keep the product memo-first rather than turning it into a rigid todo app.

Human review status: Pending

Reviewer notes:

- Confirm whether Gmail OAuth is required in MVP or can start with pasted email metadata.
- Confirm preferred first storage backend: PostgreSQL or DynamoDB.

Decision:

- Pending human approval.

## Review 002: MVP Architecture

Date: 2026-09-13

AI proposal:

- React/TypeScript frontend
- Python/FastAPI API
- Deterministic local extractor for demo and tests
- Bedrock adapter as target AI integration
- AWS target: Cognito, API Gateway, Lambda/ECS, database, Bedrock, S3, CloudFront, CloudWatch, Secrets Manager

Human review status: Pending

Decision:

- Pending human approval.

## Review 003: Security Scope

Date: 2026-09-13

AI proposal:

- Treat email content as sensitive.
- Use Gmail readonly scope initially.
- Do not log raw email content or prompts.
- Store secrets outside the repository.

Human review status: Pending

Decision:

- Pending human approval.

## Review 004: Blank Screen Report

Date: 2026-09-13

Human feedback: The screen remains white.

AI investigation and change:

- The running HTTP preview at `http://127.0.0.1:5173/` renders the memo editor
  and returns extraction results in the browser. The user's original blank
  screen has not been reproduced; its cause is not yet confirmed.
- The HTML previously had an empty root with no startup content. Add visible
  loading guidance and a local preview link so a module load failure or direct
  HTML-file opening does not leave an entirely empty page.
- Document the HTTP preview URL and the direct-file limitation.

Human review status: Pending verification of the updated preview.

## Review 005: Memo-Focused UI Redesign

Date: 2026-09-13

Human feedback: The UI looks obviously AI-generated; redesign it.
The user subsequently requested continuation after a tooling interruption.

Implemented response:

- Replace explanatory headings, nested cards, and confidence badges with a
  note library, an unframed memo editor, and a compact context inspector.
- Use restrained neutral surfaces, thin dividers, readable note text, and
  small icon controls with accessible names and tooltips.
- Connect search, note selection, new drafts, email folding/editing, saving,
  and the existing review endpoint to the UI.
- Add PUT updates so editing a saved note preserves its identity; an edit
  clears the previous review and re-extracts context on save.
- Keep re-extracted results marked unsaved until saved, and show failures
  without discarding the text in the editor.
- On narrow screens, show a collapsible note library and move context below
  the editor. See `14-ui-design.md` for the design and verification record.

Human review status: Redesign requested; final visual acceptance pending.
Automated exercise of the sample note's review button is a software test,
not human approval of design or production content.

## Review 006: Specifications, Anonymization, and First Commit

Date: 2026-09-13

Explicit human request:

- Commit the project to Git.
- Provide specifications and design documents.
- Remove real company names even from examples.

Implemented response:

- Standardize all application, test, and documentation examples on fictional
  customer/role labels, an online meeting, and a reserved example domain.
- Update the saved synthetic demo note and regenerate its extracted context.
- Add Japanese specifications, detailed design, API contracts, and testing /
  operations documentation, with implemented and proposed behavior separated.
- Correct initial artifacts that implied unimplemented data models, error
  envelopes, or unrecorded human design acceptance were already in place.
- Align CI with the existing pnpm lockfile, add repository exclusions and
  agent guidance, and initialize a project-local Git repository.
- Ask for commit attribution. With no alternative supplied, use the announced
  repository-local anonymous identity: ContextPad Bot with an invalid-domain
  address. No global Git identity is changed and no remote push is performed.

Verification:

- Five API tests passed with anonymized fixtures.
- TypeScript and Vite production build passed. The bundled pnpm wrapper tried
  to reinstall existing dependencies and stopped without a TTY; the installed
  tsc and vite binaries completed the same build pipeline directly.
- Validated 21 Markdown files, 21 local document links, and seven JSON samples.
- API documentation examples validate against Pydantic and match actual
  deterministic extraction.
- Browser reload shows the anonymized stored sample and extracted fields.
- Terraform CLI is not installed here; its validation and remote Actions
  execution remain unverified.

Human review status: Changes and commit explicitly requested. Detailed design
acceptance and production-release approval remain pending.
