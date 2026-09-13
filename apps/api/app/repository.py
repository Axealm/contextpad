from datetime import datetime, timezone

from app.models import NoteCreate, ReviewStatus, WorkNote


class NoteRepository:
    def __init__(self) -> None:
        self._notes: dict[str, WorkNote] = {}

    def list(self, query: str | None = None) -> list[WorkNote]:
        notes = sorted(self._notes.values(), key=lambda note: note.created_at, reverse=True)
        if not query:
            return notes
        normalized = query.lower()
        return [
            note
            for note in notes
            if normalized in note.title.lower()
            or normalized in note.memo.lower()
            or (note.email is not None and normalized in note.email.subject.lower())
            or any(normalized in task.lower() for task in note.context.tasks)
        ]

    def get(self, note_id: str) -> WorkNote | None:
        return self._notes.get(note_id)

    def create(self, payload: NoteCreate, context) -> WorkNote:
        note = WorkNote(title=payload.title, memo=payload.memo, email=payload.email, context=context)
        self._notes[note.id] = note
        return note

    def mark_reviewed(self, note_id: str) -> WorkNote | None:
        note = self._notes.get(note_id)
        if note is None:
            return None
        note.context.review_status = ReviewStatus.human_reviewed
        note.updated_at = datetime.now(timezone.utc)
        self._notes[note.id] = note
        return note

    def update(self, note_id: str, payload: NoteCreate, context) -> WorkNote | None:
        note = self._notes.get(note_id)
        if note is None:
            return None
        note.title = payload.title
        note.memo = payload.memo
        note.email = payload.email
        note.context = context
        note.updated_at = datetime.now(timezone.utc)
        return note
