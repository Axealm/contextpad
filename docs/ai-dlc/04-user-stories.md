# User Stories

## Planned MVP Stories

Some stories are still unimplemented, including direct editing of extracted
fields and structured search. See [current specification](../specification.md).

1. As a user, I can create a note linked to an email subject, sender, received time, and body snippet.
2. As a user, I can write a rough memo without choosing a rigid template.
3. As a user, I can ask AI to organize the email and memo into structured fields.
4. As a user, I can see extracted date/time, place, people, deadline, and tasks.
5. As a user, I can edit the structured result before saving.
6. As a user, I can search notes by keyword, person, place, task, or related email subject.
7. As a user, I can distinguish AI-generated fields from human-confirmed fields.

## Future Stories

1. As a user, I can connect Gmail using OAuth.
2. As a user, I can choose a Gmail message and create a note from it.
3. As a user, I can push confirmed tasks to a calendar or task app.
4. As a user, I can see a timeline of upcoming work extracted from my notes.
5. As a user, I can ask follow-up questions about my work context.

## Acceptance Criteria For MVP

- A new note can be created from email metadata and rough memo text.
- Structured extraction returns a deterministic response shape.
- The API returns validation errors for invalid requests.
- The frontend shows raw memo and extracted context side by side.
- Security-sensitive configuration is not hardcoded.
- AI review artifacts exist in `docs/ai-dlc`.
