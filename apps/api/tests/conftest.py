import pytest

from app.main import app
from app.repository import NoteRepository


@pytest.fixture(autouse=True)
def note_repository(tmp_path, monkeypatch):
    repository = NoteRepository(tmp_path / "test.sqlite3")
    repository.initialize()
    monkeypatch.setattr(app.state, "repository", repository, raising=False)
    yield repository
