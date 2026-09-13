# Data Model

## Target Entities (Not the Current API Schema)

Current JSON fields and nesting are documented in [design.md](../design.md).

### User

- `id`
- `email`
- `display_name`
- `created_at`

### EmailLink

- `id`
- `user_id`
- `provider`: `gmail`
- `provider_message_id`
- `subject`
- `sender`
- `received_at`
- `snippet`
- `created_at`

### WorkNote

- `id`
- `user_id`
- `email_link_id`
- `title`
- `memo`
- `status`: `draft`, `reviewed`, `archived`
- `created_at`
- `updated_at`

### ExtractedContext

- `id`
- `work_note_id`
- `summary`
- `event_datetime`
- `location`
- `deadline`
- `people`
- `tasks`
- `confidence`
- `ai_model`
- `review_status`: `ai_generated`, `human_reviewed`
- `created_at`

### ReviewEvent

- `id`
- `work_note_id`
- `actor`
- `event_type`
- `before`
- `after`
- `created_at`

## MVP Storage

The local MVP embeds EmailLink and ExtractedContext inside WorkNote in an
in-memory repository. It has no user_id, independent email entity ID, or
ReviewEvent. The target entities above require a schema migration.

## Target PostgreSQL Tables

- `users`
- `email_links`
- `work_notes`
- `extracted_contexts`
- `review_events`

## DynamoDB Alternative

For a lower-cost serverless version:

- Partition key: `USER#{user_id}`
- Sort key examples:
  - `NOTE#{note_id}`
  - `EMAIL#{email_id}`
  - `CONTEXT#{note_id}`
  - `REVIEW#{timestamp}#{event_id}`

The DynamoDB option reduces operations overhead but makes ad hoc querying harder. The MVP keeps repository boundaries so either backend can be used.
