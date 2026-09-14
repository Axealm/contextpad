import logging
import os
import secrets
import time
from dataclasses import dataclass, field
from pathlib import Path
from threading import RLock
from urllib.parse import urlsplit

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse

from app.gmail_provider import GmailError, GoogleGmailProvider
from app.models import GmailAuthorization, GmailConnectionStatus, GmailDisconnectResult, GmailMessageDetail, GmailMessagePage

PREFIX = "/api/v1/gmail"
COOKIE = "contextpad_gmail"
SESSION_TTL = 12 * 60 * 60
AUTH_TTL = 10 * 60


@dataclass(repr=False)
class GmailSettings:
    client_id: str = ""
    client_secret: str = ""
    redirect_uri: str = "http://127.0.0.1:8000/api/v1/gmail/callback"
    web_origin: str = "http://127.0.0.1:5173"

    @property
    def configured(self):
        return bool(self.client_id and self.client_secret and self.valid_urls)

    @property
    def valid_urls(self):
        try:
            web, callback = urlsplit(self.web_origin), urlsplit(self.redirect_uri)
            web.port, callback.port
        except ValueError:
            return False
        return (web.scheme == callback.scheme == "http"
                and web.hostname == callback.hostname
                and web.hostname in {"localhost", "127.0.0.1"}
                and not web.path and not web.query and not web.fragment
                and callback.path == f"{PREFIX}/callback" and not callback.query and not callback.fragment
                and not web.username and not callback.username)

    @classmethod
    def from_env(cls):
        load_dotenv(Path(__file__).resolve().parents[1] / ".env")
        return cls(
            client_id=os.getenv("GOOGLE_CLIENT_ID", "").strip(),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET", "").strip(),
            redirect_uri=os.getenv("GMAIL_REDIRECT_URI", cls.redirect_uri),
            web_origin=os.getenv("APP_WEB_ORIGIN", cls.web_origin),
        )


@dataclass(repr=False)
class GmailSession:
    expires: float
    credentials: object = None
    flow: object = None
    state: str = ""
    auth_expires: float = 0
    error: str | None = None
    lock: object = field(default_factory=RLock)


class GmailService:
    def __init__(self, settings=None, provider=None, clock=time.monotonic):
        self.settings = settings or GmailSettings.from_env()
        self.provider = provider or GoogleGmailProvider()
        self.clock = clock
        self.sessions: dict[str, GmailSession] = {}
        self.lock = RLock()

    def session(self, session_id):
        with self.lock:
            for key in list(self.sessions):
                if self.sessions[key].expires <= self.clock():
                    del self.sessions[key]
            return self.sessions.get(session_id)

    def begin(self, session_id):
        with self.lock:
            session = self.session(session_id)
            if not session:
                if len(self.sessions) >= 100:
                    raise GmailError("too_many_sessions", 429)
                session_id = secrets.token_urlsafe(32)
                session = self.sessions[session_id] = GmailSession(self.clock() + SESSION_TTL)
        with session.lock:
            session.flow, url, session.state = self.provider.begin(self.settings)
            session.auth_expires = self.clock() + AUTH_TTL
            session.error = None
            return session_id, url


service = GmailService()


def get_service():
    return service


def trusted_origin(request: Request, gmail: GmailService = Depends(get_service)):
    if request.headers.get("origin") != gmail.settings.web_origin:
        raise HTTPException(status_code=403, detail="origin_not_allowed")


def connected_session(request: Request, gmail: GmailService):
    session = gmail.session(request.cookies.get(COOKIE))
    if not session or not session.credentials:
        raise HTTPException(status_code=401, detail="reconnect_required")
    return session


def provider_call(session, call):
    with session.lock:
        if not session.credentials:
            raise HTTPException(status_code=401, detail="reconnect_required")
        try:
            return call(session.credentials)
        except GmailError as error:
            if error.status == 401:
                session.credentials = None
            raise HTTPException(status_code=error.status, detail=error.code) from None


router = APIRouter(prefix=PREFIX, tags=["gmail"])
protected = APIRouter(dependencies=[Depends(trusted_origin)])


@protected.get("/status", response_model=GmailConnectionStatus)
def status(request: Request, gmail: GmailService = Depends(get_service)):
    session = gmail.session(request.cookies.get(COOKIE))
    if session:
        with session.lock:
            if session.state and session.auth_expires <= gmail.clock():
                session.flow, session.state, session.error = None, "", "oauth_expired"
            return {"configured": gmail.settings.configured, "connected": bool(session.credentials),
                    "pending": bool(session.state), "error": session.error}
    return {"configured": gmail.settings.configured, "connected": False, "pending": False, "error": None}


@protected.post("/connect", response_model=GmailAuthorization)
def connect(request: Request, response: Response, gmail: GmailService = Depends(get_service)):
    if not gmail.settings.configured:
        raise HTTPException(status_code=503, detail="gmail_not_configured")
    try:
        session_id, url = gmail.begin(request.cookies.get(COOKIE))
    except GmailError as error:
        raise HTTPException(status_code=error.status, detail=error.code) from None
    response.set_cookie(COOKIE, session_id, httponly=True, samesite="lax", path=PREFIX, max_age=SESSION_TTL)
    return {"authorization_url": url}


@router.get("/callback")
def callback(request: Request, state: str = "", code: str = "", error: str = "", gmail: GmailService = Depends(get_service)):
    session = gmail.session(request.cookies.get(COOKIE))
    succeeded = False
    if session:
        with session.lock:
            if session.state and state and secrets.compare_digest(session.state, state):
                flow = session.flow
                session.flow, session.state = None, ""
                if session.auth_expires <= gmail.clock():
                    session.error = "oauth_expired"
                elif error or not code:
                    session.error = "consent_denied"
                else:
                    try:
                        session.credentials = gmail.provider.exchange(flow, code)
                        session.error = None
                        succeeded = True
                    except GmailError as failure:
                        session.error = failure.code
    return RedirectResponse(f"{PREFIX}/result?success={'true' if succeeded else 'false'}", status_code=303)


@router.get("/result", response_class=HTMLResponse)
def connection_result(success: bool = False):
    title = "Gmailに接続しました" if success else "Gmailに接続できませんでした"
    return HTMLResponse(
        f'<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
        f'<title>{title}</title><h1>{title}</h1><p>このタブを閉じてContextPadに戻ってください。</p></html>',
        status_code=200 if success else 400,
        headers={"Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"},
    )


@protected.get("/messages", response_model=GmailMessagePage)
def messages(request: Request, q: str = Query(default="", max_length=500), page_token: str | None = Query(default=None, max_length=2048), gmail: GmailService = Depends(get_service)):
    session = connected_session(request, gmail)
    return provider_call(session, lambda credentials: gmail.provider.list_messages(credentials, q, page_token))


@protected.get("/messages/{message_id}", response_model=GmailMessageDetail)
def message(request: Request, message_id: str, gmail: GmailService = Depends(get_service)):
    if not (1 <= len(message_id) <= 128 and message_id.isascii() and message_id.isalnum()):
        raise HTTPException(status_code=422, detail="invalid_message_id")
    session = connected_session(request, gmail)
    return provider_call(session, lambda credentials: gmail.provider.get_message(credentials, message_id))


@protected.post("/disconnect", response_model=GmailDisconnectResult)
def disconnect(request: Request, response: Response, gmail: GmailService = Depends(get_service)):
    session_id = request.cookies.get(COOKIE)
    session = gmail.session(session_id)
    revoked = True
    if session:
        with session.lock:
            credentials = session.credentials
            session.credentials, session.flow, session.state = None, None, ""
            if credentials:
                revoked = gmail.provider.revoke(credentials)
        with gmail.lock:
            gmail.sessions.pop(session_id, None)
    response.delete_cookie(COOKIE, path=PREFIX)
    return {"connected": False, "revoked": revoked}


router.include_router(protected)


class GmailAccessLogFilter(logging.Filter):
    def filter(self, record):
        # Uvicorn logs the full request target, including OAuth codes and mail queries.
        if isinstance(record.args, tuple) and len(record.args) == 5 and str(record.args[2]).startswith(PREFIX):
            args = list(record.args)
            args[2] = str(args[2]).split("?", 1)[0]
            record.args = tuple(args)
        return True


logging.getLogger("uvicorn.access").addFilter(GmailAccessLogFilter())
