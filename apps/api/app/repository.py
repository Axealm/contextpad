import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from app.models import ExtractedContext, NoteCreate, ReviewStatus, WorkNote

API_DIRECTORY = Path(__file__).resolve().parents[1]
COLUMNS = "id, title, memo, email_json, context_json, created_at, updated_at"


def database_path() -> Path:
    configured = Path(os.getenv("CONTEXTPAD_DB_PATH") or "data/contextpad.sqlite3").expanduser()
    return (API_DIRECTORY / configured).resolve()


class StorageError(Exception):
    """A storage failure with no note content or filesystem path in its message."""


class NoteRepository:
    def __init__(self, path: Path) -> None:
        self.path = path

    @contextmanager
    def _connection(self, *, write: bool = False):
        connection = None
        try:
            # Each request owns its connection; read-modify-write operations lock first.
            connection = sqlite3.connect(self.path, timeout=5, isolation_level=None)
            connection.row_factory = sqlite3.Row
            connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield connection
            connection.commit()
        except (sqlite3.Error, ValidationError, json.JSONDecodeError):
            raise StorageError("storage_unavailable") from None
        finally:
            if connection is not None:
                try:
                    if connection.in_transaction:
                        connection.rollback()
                finally:
                    connection.close()

    def initialize(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            raise StorageError("storage_unavailable") from None
        with self._connection(write=True) as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version == 0:
                tables = connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                if tables:
                    raise StorageError("unsupported_database_schema")
                connection.execute("""
                    CREATE TABLE notes (
                        id TEXT PRIMARY KEY NOT NULL,
                        title TEXT NOT NULL,
                        memo TEXT NOT NULL,
                        email_json TEXT,
                        context_json TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                connection.execute("CREATE INDEX notes_created_at ON notes(created_at DESC, id)")
                connection.execute("PRAGMA user_version = 1")
            elif version != 1:
                raise StorageError("unsupported_database_schema")
            if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise StorageError("storage_unavailable")
            connection.execute(f"SELECT {COLUMNS} FROM notes LIMIT 0")

    @staticmethod
    def _decode(row: sqlite3.Row) -> WorkNote:
        return WorkNote(
            id=row["id"], title=row["title"], memo=row["memo"],
            email=json.loads(row["email_json"]) if row["email_json"] is not None else None,
            context=json.loads(row["context_json"]),
            created_at=row["created_at"], updated_at=row["updated_at"],
        )

    @staticmethod
    def _values(note: WorkNote) -> tuple:
        return (
            note.id, note.title, note.memo,
            note.email.model_dump_json() if note.email is not None else None,
            note.context.model_dump_json(),
            note.created_at.isoformat(), note.updated_at.isoformat(),
        )

    def list(self, query: str | None = None) -> list[WorkNote]:
        with self._connection() as connection:
            notes = [self._decode(row) for row in connection.execute(
                f"SELECT {COLUMNS} FROM notes ORDER BY created_at DESC, id"
            )]
        if not query:
            return notes
        normalized = query.lower()
        return [
            note for note in notes
            if normalized in note.title.lower()
            or normalized in note.memo.lower()
            or (note.email is not None and normalized in note.email.subject.lower())
            or any(normalized in task.lower() for task in note.context.tasks)
        ]

    def get(self, note_id: str) -> WorkNote | None:
        with self._connection() as connection:
            row = connection.execute(f"SELECT {COLUMNS} FROM notes WHERE id = ?", (note_id,)).fetchone()
            return self._decode(row) if row else None

    def create(self, payload: NoteCreate, context: ExtractedContext) -> WorkNote:
        note = WorkNote(title=payload.title, memo=payload.memo, email=payload.email, context=context)
        with self._connection(write=True) as connection:
            connection.execute(f"INSERT INTO notes ({COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?)", self._values(note))
        return note

    def mark_reviewed(self, note_id: str) -> WorkNote | None:
        with self._connection(write=True) as connection:
            row = connection.execute(f"SELECT {COLUMNS} FROM notes WHERE id = ?", (note_id,)).fetchone()
            if row is None:
                return None
            note = self._decode(row)
            note.context.review_status = ReviewStatus.human_reviewed
            note.updated_at = datetime.now(timezone.utc)
            connection.execute("UPDATE notes SET context_json = ?, updated_at = ? WHERE id = ?", (
                note.context.model_dump_json(), note.updated_at.isoformat(), note_id,
            ))
            return note

    def update(self, note_id: str, payload: NoteCreate, context: ExtractedContext) -> WorkNote | None:
        with self._connection(write=True) as connection:
            row = connection.execute(f"SELECT {COLUMNS} FROM notes WHERE id = ?", (note_id,)).fetchone()
            if row is None:
                return None
            previous = self._decode(row)
            note = WorkNote(
                id=previous.id, created_at=previous.created_at,
                title=payload.title, memo=payload.memo, email=payload.email, context=context,
            )
            values = self._values(note)
            connection.execute("""
                UPDATE notes SET title = ?, memo = ?, email_json = ?, context_json = ?,
                    created_at = ?, updated_at = ? WHERE id = ?
            """, (*values[1:], note_id))
            return note
