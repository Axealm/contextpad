# API Design

Initial design notes. The authoritative implemented contract, including
FastAPI's actual errors, is [API reference](../api-reference.md).

Base URL:

```text
/api/v1
```

## Endpoints

### Health

`GET /health`

Response:

```json
{
  "status": "ok"
}
```

### Create Note

`POST /api/v1/notes`

Request:

```json
{
  "title": "9/17 取引先A 打ち合わせ",
  "memo": "担当Aさん参加。前回資料確認。明日午前中ドラフト作る。",
  "email": {
    "provider": "gmail",
    "provider_message_id": "gmail-message-id",
    "subject": "9/17 取引先A打ち合わせについて",
    "sender": "contact@example.invalid",
    "received_at": "2026-09-12T09:00:00+09:00",
    "snippet": "9/17 14:00からオンラインで..."
  }
}
```

Response:

```json
{
  "id": "note-id",
  "title": "9/17 取引先A 打ち合わせ",
  "memo": "...",
  "email": {},
  "context": {},
  "created_at": "2026-09-13T00:00:00Z"
}
```

### Extract Context

`POST /api/v1/extract`

Runs extraction without saving.

### List Notes

`GET /api/v1/notes?query=取引先A`

### Get Note

`GET /api/v1/notes/{note_id}`

### Update Note

`PUT /api/v1/notes/{note_id}`

Uses the create-note request shape. Preserves the note ID and creation time,
re-extracts context, and resets the context review status. Returns the updated
note, 404 for an unknown ID, or 422 for invalid input.

### Review Context

`POST /api/v1/notes/{note_id}/review`

Marks the extracted context as human-reviewed.

## Proposed Error Shape (Not Implemented)

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "memo is required",
    "details": {}
  }
}
```
