import base64
import json
import logging
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest
import requests
from fastapi.testclient import TestClient
from google.oauth2.credentials import Credentials

from app.gmail import AUTH_TTL, COOKIE, PREFIX, SESSION_TTL, GmailAccessLogFilter, GmailService, GmailSettings, get_service
from app.gmail_provider import BODY_LIMIT, SCOPE, GmailError, GoogleGmailProvider, email_from_message
from app.main import app

ORIGIN = "http://127.0.0.1:5173"


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Live network is forbidden in Gmail tests")
    monkeypatch.setattr(requests.sessions.Session, "request", blocked)


class FakeProvider:
    def __init__(self):
        self.exchanges = 0
        self.failure = None
        self.revoked = True
        self.calls = []

    def begin(self, settings):
        return object(), "https://accounts.google.com/o/oauth2/auth?state=test-state", "test-state"

    def exchange(self, flow, code):
        self.exchanges += 1
        if self.failure:
            raise self.failure
        assert code == "test-code"
        return SimpleNamespace(token="synthetic-token", refresh_token="synthetic-refresh")

    def list_messages(self, credentials, query, token):
        self.calls.append((query, token))
        if self.failure:
            raise self.failure
        return {"messages": [], "next_page_token": "page-two"}

    def get_message(self, credentials, message_id):
        return email_from_message(sample_message(message_id), full=True)

    def revoke(self, credentials):
        return self.revoked


@pytest.fixture
def context():
    provider = FakeProvider()
    now = [100.0]
    service = GmailService(GmailSettings("synthetic-client", "synthetic-secret"), provider, clock=lambda: now[0])
    app.dependency_overrides[get_service] = lambda: service
    with TestClient(app, base_url="http://127.0.0.1:8000", headers={"Origin": ORIGIN}) as client:
        yield client, service, provider, now
    app.dependency_overrides.clear()


def authorize(client):
    assert client.post(f"{PREFIX}/connect").status_code == 200
    return client.get(f"{PREFIX}/callback", params={"state": "test-state", "code": "test-code"})


def test_configuration_and_origin_boundary(context):
    client, service, provider, _ = context
    service.settings.client_secret = ""
    assert client.get(f"{PREFIX}/status").json()["configured"] is False
    assert client.post(f"{PREFIX}/connect").status_code == 503
    for method, path in [("GET", "/status"), ("POST", "/connect"), ("POST", "/disconnect"), ("GET", "/messages")]:
        assert client.request(method, PREFIX + path, headers={"Origin": "https://untrusted.example.invalid"}).status_code == 403
    assert client.get(f"{PREFIX}/status", headers={"Host": "untrusted.example.invalid"}).status_code == 400
    assert provider.exchanges == 0


def test_oauth_cookie_and_state_are_bound_to_browser_and_single_use(context):
    client, service, provider, _ = context
    response = client.post(f"{PREFIX}/connect")
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie and f"Path={PREFIX}" in cookie
    assert "synthetic-secret" not in response.text
    with TestClient(app, base_url="http://127.0.0.1:8000", headers={"Origin": ORIGIN}) as stranger:
        assert stranger.get(f"{PREFIX}/callback?state=test-state&code=test-code").status_code == 400
        assert stranger.get(f"{PREFIX}/messages").status_code == 401
    assert client.get(f"{PREFIX}/callback?state=wrong&code=test-code").status_code == 400
    response = client.get(f"{PREFIX}/callback?state=test-state&code=test-code")
    assert response.status_code == 200
    assert "code=" not in str(response.url) and response.history[0].status_code == 303
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "default-src 'none'" in response.headers["content-security-policy"]
    assert "synthetic-token" not in response.text
    assert client.get(f"{PREFIX}/callback?state=test-state&code=test-code").status_code == 400
    assert provider.exchanges == 1
    assert client.get(f"{PREFIX}/status").json()["connected"] is True


@pytest.mark.parametrize("outcome", ["denied", "expired", "failed"])
def test_failed_oauth_preserves_disconnected_state(context, outcome):
    client, service, provider, now = context
    client.post(f"{PREFIX}/connect")
    params = {"state": "test-state", "code": "test-code"}
    if outcome == "denied":
        params["error"] = "access_denied"
    elif outcome == "expired":
        now[0] += AUTH_TTL + 1
    else:
        provider.failure = GmailError("oauth_failed")
    assert client.get(f"{PREFIX}/callback", params=params).status_code == 400
    status = client.get(f"{PREFIX}/status").json()
    assert not status["connected"] and not status["pending"] and status["error"]
    assert client.get(f"{PREFIX}/messages").status_code == 401


def test_expired_session_and_poll_timeout(context):
    client, service, _, now = context
    client.post(f"{PREFIX}/connect")
    now[0] += AUTH_TTL + 1
    assert client.get(f"{PREFIX}/status").json()["error"] == "oauth_expired"
    assert authorize(client).status_code == 200
    now[0] += SESSION_TTL + 1
    assert not client.get(f"{PREFIX}/status").json()["connected"]
    assert not service.sessions


def test_gmail_search_selection_and_note_link(context):
    client, _, provider, _ = context
    authorize(client)
    response = client.get(f"{PREFIX}/messages", params={"q": "from:contact@example.invalid", "page_token": "page-two"})
    assert response.status_code == 200
    assert provider.calls == [("from:contact@example.invalid", "page-two")]
    email = client.get(f"{PREFIX}/messages/abc123").json()["email"]
    note = client.post("/api/v1/notes", json={"title": "取引先A", "memo": "前回資料確認", "email": email}).json()
    assert note["email"]["provider_message_id"] == "abc123"
    assert note["context"]["event_datetime"] == "9/17 14:00"
    assert client.get(f"{PREFIX}/messages/bad-id").status_code == 422
    assert client.get(f"{PREFIX}/messages", params={"q": "x" * 501}).status_code == 422


@pytest.mark.parametrize("revoked", [True, False])
def test_disconnect_clears_local_tokens_even_if_remote_revoke_fails(context, revoked):
    client, service, provider, _ = context
    authorize(client)
    provider.revoked = revoked
    response = client.post(f"{PREFIX}/disconnect")
    assert response.json() == {"connected": False, "revoked": revoked}
    assert not service.sessions and COOKIE not in client.cookies
    assert client.get(f"{PREFIX}/messages").status_code == 401


@pytest.mark.parametrize("status,code,connected", [(401, "reconnect_required", False), (429, "rate_limited", True), (502, "gmail_unavailable", True)])
def test_provider_errors_are_sanitized(context, status, code, connected):
    client, _, provider, _ = context
    authorize(client)
    provider.failure = GmailError(code, status)
    response = client.get(f"{PREFIX}/messages")
    assert response.status_code == status and response.json() == {"detail": code}
    assert client.get(f"{PREFIX}/status").json()["connected"] is connected


def part(text, mime="text/plain", **extra):
    return {"mimeType": mime, "body": {"data": base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")}, **extra}


def sample_message(message_id="abc123"):
    return {"id": message_id, "snippet": "短い抜粋", "internalDate": "1789340400000", "payload": part(
        "9/17 14:00 オンラインで取引先Aと打ち合わせ", headers=[
            {"name": "Subject", "value": "取引先A 打ち合わせ"}, {"name": "From", "value": "contact@example.invalid"},
        ],
    )}


def test_mime_plain_alternative_html_and_attachments():
    message = sample_message()
    message["payload"] = {"mimeType": "multipart/mixed", "parts": [
        {"mimeType": "multipart/alternative", "parts": [part("<p>HTML版</p>", "text/html"), part("本文の改行\n担当Aさん")]},
        part("添付の秘密", filename="sample.txt"),
    ]}
    result = email_from_message(message, full=True)
    assert result["email"]["snippet"] == "本文の改行\n担当Aさん"
    assert not result["snippet_only"]
    message["payload"] = part('<p>確認 &amp; 共有</p><script>alert(1)</script><style>secret</style><img src="https://example.invalid/tracker">', "text/html")
    assert email_from_message(message, full=True)["email"]["snippet"] == "確認 & 共有"
    message["payload"] = {"mimeType": "text/plain", "body": {"attachmentId": "not-fetched"}}
    assert email_from_message(message, full=True)["snippet_only"] is True
    message["payload"] = part("あ" * (BODY_LIMIT + 20))
    result = email_from_message(message, full=True)
    assert len(result["email"]["snippet"]) == BODY_LIMIT and result["truncated"]


def test_real_oauth_library_uses_readonly_pkce_and_fixed_callback():
    settings = GmailSettings("synthetic-client", "synthetic-secret")
    flow, url, state = GoogleGmailProvider().begin(settings)
    params = parse_qs(urlsplit(url).query)
    assert params["scope"] == [SCOPE]
    assert params["redirect_uri"] == [settings.redirect_uri]
    assert params["code_challenge_method"] == ["S256"]
    assert params["state"] == [state] and len(state) >= 30 and flow.code_verifier
    assert "synthetic-secret" not in url


def test_real_provider_refreshes_expired_access_token(monkeypatch):
    calls = []
    def send(session, method, url, **kwargs):
        calls.append((method, url, kwargs))
        response = requests.Response()
        response.status_code = 200
        response.headers["Content-Type"] = "application/json"
        if url == "https://oauth2.googleapis.com/token":
            payload = {"access_token": "synthetic-new-token", "expires_in": 3600, "token_type": "Bearer"}
        else:
            assert kwargs["headers"]["authorization"] == "Bearer synthetic-new-token"
            payload = {"messages": []}
        response._content = json.dumps(payload).encode()
        return response
    monkeypatch.setattr(requests.sessions.Session, "request", send)
    credentials = Credentials(None, refresh_token="synthetic-refresh", token_uri="https://oauth2.googleapis.com/token", client_id="synthetic-client", client_secret="synthetic-secret", scopes=[SCOPE])
    assert GoogleGmailProvider().list_messages(credentials, "", None)["messages"] == []
    assert calls[0][1] == "https://oauth2.googleapis.com/token"
    assert credentials.token == "synthetic-new-token"


def test_mail_metadata_paging_does_not_fetch_bodies(monkeypatch):
    requests_seen = []
    def send(session, method, url, **kwargs):
        requests_seen.append((url, kwargs.get("params")))
        response = requests.Response()
        response.status_code = 200
        payload = {"messages": [{"id": "abc123"}], "nextPageToken": "next"} if url.endswith("/messages") else sample_message()
        response._content = json.dumps(payload).encode()
        return response
    monkeypatch.setattr(requests.sessions.Session, "request", send)
    result = GoogleGmailProvider().list_messages(Credentials("synthetic-token"), "取引先A", "previous")
    assert requests_seen[0][1]["pageToken"] == "previous"
    assert requests_seen[1][1]["format"] == "metadata"
    assert result["next_page_token"] == "next"
    assert result["messages"][0]["snippet"] == "短い抜粋"


def test_oauth_access_logs_do_not_keep_codes_or_searches():
    record = logging.LogRecord("uvicorn.access", logging.INFO, "", 0, "%s %s %s %s %s", ("local", "GET", f"{PREFIX}/callback?code=secret&state=state", "1.1", 200), None)
    assert GmailAccessLogFilter().filter(record)
    assert "secret" not in record.getMessage() and "?" not in record.getMessage()
