import json
import os
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing

import pytest
from fastapi.testclient import TestClient

from app.extractor import ContextExtractor
from app.main import app, create_app
from app.models import EmailLink, NoteCreate, ReviewStatus
from app.repository import API_DIRECTORY, NoteRepository, StorageError, database_path


def create_note(repository, title="Fixture A"):
    payload = NoteCreate(
        title=title, memo="Prepare draft",
        email=EmailLink(
            provider_message_id="a123", subject="Meeting", sender="contact@example.invalid",
            received_at="2026-09-14T00:00:00Z", snippet="Synthetic message",
        ),
    )
    return repository.create(payload, ContextExtractor().extract(payload.memo, payload.email))


def test_reopen_preserves_note_email_timestamps_and_review(note_repository):
    note = create_note(note_repository)
    reviewed = note_repository.mark_reviewed(note.id)
    reopened = NoteRepository(note_repository.path)
    reopened.initialize()
    assert reopened.get(note.id) == reviewed
    assert reviewed.created_at == note.created_at
    assert reviewed.context.review_status == ReviewStatus.human_reviewed
    assert reopened.list() == [reviewed]


def test_update_survives_reopen_and_removes_previous_email_and_review(note_repository):
    note = create_note(note_repository)
    note_repository.mark_reviewed(note.id)
    payload = NoteCreate(title="Edited", memo="Changed memo", email=None)
    updated = note_repository.update(note.id, payload, ContextExtractor().extract(payload.memo))
    stored = NoteRepository(note_repository.path).get(note.id)
    assert stored == updated
    assert stored.id == note.id and stored.created_at == note.created_at
    assert stored.updated_at >= note.updated_at
    assert stored.email is None
    assert stored.context.review_status == ReviewStatus.ai_generated
    assert len(note_repository.list()) == 1


def test_search_is_literal_case_insensitive_and_supports_all_previous_fields(note_repository):
    first = create_note(note_repository, "100%_ ' OR 1=1; --")
    payload = NoteCreate(title="\u53d6\u5f15\u5148B", memo="\u8cc7\u6599\u78ba\u8a8d")
    context = ContextExtractor().extract(payload.memo)
    context.tasks = ["Task-only match"]
    second = note_repository.create(payload, context)
    assert note_repository.list("%_") == [first]
    assert note_repository.list("' OR 1=1; --") == [first]
    assert note_repository.list("MEETING") == [first]
    assert note_repository.list("\u8cc7\u6599") == [second]
    assert note_repository.list("task-only") == [second]
    assert note_repository.list("not-present") == []
    assert note_repository.list() == [second, first]
    assert note_repository.get("' OR 1=1; --") is None


def test_failed_update_rolls_back_every_field(note_repository):
    note = create_note(note_repository)
    with closing(sqlite3.connect(note_repository.path)) as connection:
        connection.execute("""
            CREATE TRIGGER reject_update BEFORE UPDATE ON notes
            BEGIN SELECT RAISE(ABORT, 'synthetic-sensitive-detail'); END
        """)
        connection.commit()
    payload = NoteCreate(title="Should not save", memo="New text")
    with pytest.raises(StorageError, match="^storage_unavailable$"):
        note_repository.update(note.id, payload, ContextExtractor().extract(payload.memo))
    assert note_repository.get(note.id) == note


def test_parallel_requests_have_independent_connections(note_repository):
    with ThreadPoolExecutor(max_workers=8) as pool:
        notes = list(pool.map(lambda i: create_note(note_repository, f"Fixture {i}"), range(16)))
        reviewed = list(pool.map(lambda note: note_repository.mark_reviewed(note.id), notes))
    assert len({note.id for note in notes}) == 16
    assert {note.id for note in note_repository.list()} == {note.id for note in notes}
    assert all(note.context.review_status == ReviewStatus.human_reviewed for note in reviewed)


@pytest.mark.parametrize("kind", ["corrupt", "unknown-table", "future-version"])
def test_invalid_database_is_rejected_without_replacing_it(tmp_path, kind):
    path = tmp_path / "invalid.sqlite3"
    if kind == "corrupt":
        path.write_bytes(b"This is not a database. Keep this file.")
    else:
        with closing(sqlite3.connect(path)) as connection:
            connection.execute("CREATE TABLE unrelated (content TEXT)")
            if kind == "future-version":
                connection.execute("PRAGMA user_version = 99")
            connection.commit()
    original = path.read_bytes()
    with pytest.raises(StorageError):
        NoteRepository(path).initialize()
    assert path.read_bytes() == original


def test_corrupt_document_returns_safe_error_and_is_not_silently_skipped(note_repository):
    note = create_note(note_repository)
    with closing(sqlite3.connect(note_repository.path)) as connection:
        connection.execute("UPDATE notes SET context_json = ? WHERE id = ?", ("sensitive-invalid-json", note.id))
        connection.commit()
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        response = client.get("/api/v1/notes")
    assert response.status_code == 503
    assert response.json() == {"detail": "storage_unavailable"}
    assert response.headers["cache-control"] == "no-store"
    assert str(note_repository.path) not in response.text


def test_unwritable_database_does_not_fall_back_to_memory(tmp_path):
    with pytest.raises(StorageError):
        with TestClient(create_app(tmp_path), base_url="http://127.0.0.1:8000"):
            pytest.fail("A directory cannot be used as the database")


def test_default_and_relative_paths_do_not_depend_on_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("CONTEXTPAD_DB_PATH", raising=False)
    assert database_path() == API_DIRECTORY / "data/contextpad.sqlite3"
    monkeypatch.setenv("CONTEXTPAD_DB_PATH", "data/other.sqlite3")
    assert database_path() == API_DIRECTORY / "data/other.sqlite3"
    monkeypatch.setenv("CONTEXTPAD_DB_PATH", str(tmp_path / "absolute.sqlite3"))
    assert database_path() == tmp_path / "absolute.sqlite3"


def test_api_data_survives_new_python_process(tmp_path):
    script = """
import json, sys
from fastapi.testclient import TestClient
from app.main import app
with TestClient(app, base_url='http://127.0.0.1:8000') as client:
    if sys.argv[1] == 'write':
        note = client.post('/api/v1/notes', json={'title': 'Restart fixture', 'memo': 'Check draft',
            'email': {'provider': 'gmail', 'provider_message_id': 'a123', 'subject': 'Fixture',
                'sender': 'contact@example.invalid', 'snippet': 'Synthetic message'}}).json()
        updated = client.put('/api/v1/notes/' + note['id'], json={
            'title': 'Updated fixture', 'memo': 'Check updated draft', 'email': note['email']})
        assert updated.status_code == 200
        response = client.post('/api/v1/notes/' + note['id'] + '/review')
    else:
        response = client.get('/api/v1/notes')
    assert response.status_code == 200
    print(json.dumps(response.json()))
"""
    environment = {**os.environ, "CONTEXTPAD_DB_PATH": str(tmp_path / "restart.sqlite3"),
                   "GOOGLE_CLIENT_ID": "", "GOOGLE_CLIENT_SECRET": ""}
    def run(mode):
        result = subprocess.run(
            [sys.executable, "-c", script, mode], cwd=API_DIRECTORY, env=environment,
            capture_output=True, text=True, check=True, timeout=30,
        )
        return json.loads(result.stdout)
    saved = run("write")
    assert run("read") == [saved]
    assert saved["context"]["review_status"] == "human_reviewed"
    assert saved["title"] == "Updated fixture"
