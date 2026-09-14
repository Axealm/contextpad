import copy
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app, create_app

ORIGIN = "http://127.0.0.1:5173"


@pytest.fixture
def client():
    with TestClient(app, base_url="http://127.0.0.1:8000", headers={"Origin": ORIGIN}) as client:
        yield client


def note(client, title="Fixture A"):
    response = client.post("/api/v1/notes", json={
        "title": title, "memo": "Check draft",
        "email": {"provider": "gmail", "subject": "Synthetic mail", "sender": "contact@example.invalid",
                  "provider_message_id": "a123", "snippet": "Synthetic body"},
    })
    assert response.status_code == 200
    return response.json()


def test_backup_delete_restore_and_restart_preserve_all_content(client, tmp_path):
    saved = note(client)
    reviewed = client.post(f"/api/v1/notes/{saved['id']}/review").json()
    exported = client.get("/api/v1/backups")
    assert exported.status_code == 200
    assert exported.headers["cache-control"] == "no-store"
    assert "attachment" in exported.headers["content-disposition"]
    backup = exported.json()
    assert backup["notes"] == [reviewed]
    assert set(backup) == {"schema_version", "exported_at", "notes"}
    assert client.delete(f"/api/v1/notes/{saved['id']}").status_code == 204
    assert client.get(f"/api/v1/notes/{saved['id']}").status_code == 404
    assert client.delete(f"/api/v1/notes/{saved['id']}").status_code == 404
    assert client.post("/api/v1/backups/restore", json=backup).json() == {"restored": 1, "skipped": 0}
    assert client.get(f"/api/v1/notes/{saved['id']}").json() == reviewed
    assert client.post("/api/v1/backups/restore", json=backup).json() == {"restored": 0, "skipped": 1}
    restored_path = tmp_path / "restored.sqlite3"
    with TestClient(create_app(restored_path), base_url="http://127.0.0.1:8000") as other:
        assert other.post("/api/v1/backups/restore", json=backup).status_code == 200
    with TestClient(create_app(restored_path), base_url="http://127.0.0.1:8000") as reopened:
        assert reopened.get("/api/v1/notes").json() == [reviewed]


def test_conflicting_backup_rolls_back_new_notes_and_keeps_current_version(client):
    existing = note(client)
    new = note(client, "Fixture B")
    backup = client.get("/api/v1/backups").json()
    assert backup["notes"][0]["id"] == new["id"]
    client.delete(f"/api/v1/notes/{new['id']}")
    changed = client.put(f"/api/v1/notes/{existing['id']}", json={"title": "Edited", "memo": "Keep this"}).json()
    response = client.post("/api/v1/backups/restore", json=backup)
    assert response.status_code == 409
    assert response.json() == {"detail": "backup_conflict"}
    assert client.get("/api/v1/notes").json() == [changed]


@pytest.mark.parametrize("change", ["version", "duplicate", "id", "timestamp", "blank", "context", "extra"])
def test_invalid_backup_is_rejected_without_partial_changes(client, change):
    saved = note(client)
    backup = client.get("/api/v1/backups").json()
    if change == "version":
        backup["schema_version"] = 2
    elif change == "duplicate":
        backup["notes"].append(copy.deepcopy(backup["notes"][0]))
    elif change == "id":
        backup["notes"][0]["id"] = "../notes/other"
    elif change == "timestamp":
        backup["notes"][0]["created_at"] = "2026-09-14T00:00:00"
    elif change == "blank":
        backup["notes"][0]["memo"] = "  "
    elif change == "context":
        backup["notes"][0]["context"]["review_status"] = "unexpected"
    else:
        backup["credentials"] = "synthetic-sensitive-content"
    response = client.post("/api/v1/backups/restore", json=backup)
    assert response.status_code == 422
    assert response.json() == {"detail": "invalid_backup"}
    assert client.get("/api/v1/notes").json() == [saved]


def test_malformed_wrong_type_and_large_stream_are_rejected(client):
    assert client.post("/api/v1/backups/restore", content="not json", headers={"Content-Type": "application/json"}).status_code == 422
    assert client.post("/api/v1/backups/restore", content="{}", headers={"Content-Type": "text/plain"}).status_code == 415
    chunks = (b" " * 1024 * 1024 for _ in range(6))
    assert client.post("/api/v1/backups/restore", content=chunks, headers={"Content-Type": "application/json"}).status_code == 413
    assert client.get("/api/v1/notes").json() == []


def test_backup_limit_never_produces_a_file_that_cannot_be_restored(client):
    note(client)
    import app.main as main
    from unittest.mock import patch
    with patch.object(main, "BACKUP_LIMIT", 1):
        assert client.get("/api/v1/backups").status_code == 413
    backup = client.get("/api/v1/backups").json()
    backup["notes"] *= 1001
    assert client.post("/api/v1/backups/restore", content=json.dumps(backup), headers={"Content-Type": "application/json"}).status_code == 422


@pytest.mark.parametrize("headers", [{"Origin": "https://untrusted.example.invalid"}, {"Origin": "null"}])
def test_foreign_websites_cannot_mutate_saved_notes(client, headers):
    saved = note(client)
    for method, path, payload in [
        ("DELETE", f"/api/v1/notes/{saved['id']}", None),
        ("POST", f"/api/v1/notes/{saved['id']}/review", None),
        ("PUT", f"/api/v1/notes/{saved['id']}", {"title": "x", "memo": "x"}),
        ("POST", "/api/v1/backups/restore", {}),
    ]:
        assert client.request(method, path, headers=headers, json=payload).status_code == 403
    assert client.get(f"/api/v1/notes/{saved['id']}").json() == saved


def test_cross_site_write_without_origin_is_also_rejected(client):
    saved = note(client)
    with TestClient(app, base_url="http://127.0.0.1:8000") as stranger:
        assert stranger.post(f"/api/v1/notes/{saved['id']}/review", headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403


def test_blank_input_is_not_saved(client):
    assert client.post("/api/v1/notes", json={"title": " ", "memo": "draft"}).status_code == 422
    assert client.post("/api/v1/notes", json={"title": "Fixture", "memo": "\n\t "}).status_code == 422
    assert client.get("/api/v1/notes").json() == []
    assert client.post("/api/v1/extract", json={"memo": "\n\t "}).status_code == 422


def test_openapi_document_has_resolvable_local_references(client):
    schema = client.get("/openapi.json").json()
    def check(value):
        if isinstance(value, dict):
            if "$ref" in value:
                assert value["$ref"].startswith("#/")
                target = schema
                for part in value["$ref"][2:].split("/"):
                    target = target[part.replace("~1", "/").replace("~0", "~")]
            for item in value.values():
                check(item)
        elif isinstance(value, list):
            for item in value:
                check(item)
    check(schema)
