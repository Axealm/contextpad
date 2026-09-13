from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_note_returns_extracted_context():
    response = client.post(
        "/api/v1/notes",
        json={
            "title": "取引先A 打ち合わせ",
            "memo": "担当Aさん参加\n前回資料確認\n明日午前中ドラフト作る",
            "email": {
                "provider": "gmail",
                "subject": "9/17 取引先A打ち合わせについて",
                "sender": "contact@example.invalid",
                "snippet": "9/17 14:00からオンラインで取引先Aとの打ち合わせです。",
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["context"]["event_datetime"] == "9/17 14:00"
    assert body["context"]["location"] == "オンライン"
    assert body["context"]["review_status"] == "ai_generated"


def test_edit_saved_note_keeps_id_and_invalidates_previous_review():
    note = client.post("/api/v1/notes", json={"title": "変更前", "memo": "前回資料確認"}).json()
    client.post(f"/api/v1/notes/{note['id']}/review")
    count_before = len(client.get("/api/v1/notes").json())

    updated = client.put(f"/api/v1/notes/{note['id']}", json={
        "title": "変更後", "memo": "担当Bさんに確認", "email": None,
    })
    assert updated.status_code == 200
    body = updated.json()
    assert body["id"] == note["id"]
    assert body["created_at"] == note["created_at"]
    assert body["title"] == "変更後"
    assert body["memo"] == "担当Bさんに確認"
    assert body["context"]["people"] == ["担当Bさん"]
    assert body["context"]["review_status"] == "ai_generated"
    assert len(client.get("/api/v1/notes").json()) == count_before
    assert client.get(f"/api/v1/notes/{note['id']}").json() == body


def test_update_missing_note_and_invalid_input():
    assert client.put("/api/v1/notes/does-not-exist", json={
        "title": "確認", "memo": "前回資料確認",
    }).status_code == 404
    note = client.post("/api/v1/notes", json={"title": "確認", "memo": "前回資料確認"}).json()
    assert client.put(f"/api/v1/notes/{note['id']}", json={
        "title": "確認", "memo": "",
    }).status_code == 422
    assert client.get(f"/api/v1/notes/{note['id']}").json() == note
