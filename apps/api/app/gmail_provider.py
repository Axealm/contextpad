import base64
import binascii
from datetime import datetime, timezone
from email.message import Message
from html import unescape
from html.parser import HTMLParser

import requests
from google.auth.exceptions import GoogleAuthError, TransportError
from google.auth.transport.requests import AuthorizedSession
from google_auth_oauthlib.flow import Flow
from oauthlib.oauth2 import OAuth2Error

from app.models import EmailLink

SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
BODY_LIMIT = 20_000


class GmailError(Exception):
    def __init__(self, code: str, status: int = 502):
        self.code = code
        self.status = status
        super().__init__(code)


class TextFromHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.fragments: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "head"}:
            self.hidden += 1
        elif not self.hidden and tag in {"p", "div", "br", "li", "tr"}:
            self.fragments.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "head"} and self.hidden:
            self.hidden -= 1

    def handle_data(self, data):
        if not self.hidden:
            self.fragments.append(data)


def body_text(part: dict, depth: int = 0) -> str:
    if depth > 20 or part.get("filename"):
        return ""
    mime = part.get("mimeType", "")
    children = part.get("parts", [])
    if mime == "multipart/alternative":
        children = sorted(children, key=lambda item: item.get("mimeType") != "text/plain")
        return next((text for child in children if (text := body_text(child, depth + 1))), "")
    if mime.startswith("multipart/"):
        return "\n".join(filter(None, (body_text(child, depth + 1) for child in children)))[:BODY_LIMIT + 1]
    if mime not in {"text/plain", "text/html"}:
        return ""
    data = part.get("body", {}).get("data", "")
    if not data:
        return ""
    headers = {header["name"].lower(): header["value"] for header in part.get("headers", [])}
    content_type = Message()
    content_type["content-type"] = headers.get("content-type", mime)
    # Decode only a bounded prefix. Attachments and external HTML resources are never fetched.
    data = data[:262_144]
    try:
        raw = base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))
        text = raw.decode(content_type.get_content_charset() or "utf-8", errors="replace")
    except LookupError:
        text = raw.decode("utf-8", errors="replace")
    except (ValueError, binascii.Error):
        return ""
    if mime == "text/html":
        parser = TextFromHTML()
        parser.feed(text)
        text = "".join(parser.fragments)
    return text.strip()[:BODY_LIMIT + 1]


def email_from_message(message: dict, full: bool = False) -> dict:
    headers = {header["name"].lower(): header["value"] for header in message.get("payload", {}).get("headers", [])}
    received_at = None
    try:
        received_at = datetime.fromtimestamp(int(message["internalDate"]) / 1000, tz=timezone.utc)
    except (KeyError, ValueError, OverflowError, OSError):
        pass
    text = body_text(message.get("payload", {})) if full else ""
    fallback = full and not text
    text = text or unescape(message.get("snippet", ""))
    email = EmailLink(
        provider_message_id=message["id"], subject=headers.get("subject", ""),
        sender=headers.get("from", ""), received_at=received_at, snippet=text[:BODY_LIMIT],
    )
    return {"email": email.model_dump(mode="json"), "truncated": len(text) > BODY_LIMIT, "snippet_only": fallback}


class GoogleGmailProvider:
    def begin(self, settings):
        flow = Flow.from_client_config({"web": {
            "client_id": settings.client_id, "client_secret": settings.client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }}, scopes=[SCOPE], redirect_uri=settings.redirect_uri, autogenerate_code_verifier=True)
        url, state = flow.authorization_url(access_type="offline", prompt="consent")
        return flow, url, state

    def exchange(self, flow, code: str):
        try:
            flow.fetch_token(code=code, timeout=15)
            credentials = flow.credentials
            granted = credentials.granted_scopes if credentials.granted_scopes is not None else credentials.scopes or []
            if SCOPE not in granted:
                raise GmailError("scope_missing", 403)
            return credentials
        except (OAuth2Error, GoogleAuthError, requests.RequestException, ValueError):
            raise GmailError("oauth_failed") from None

    def _session(self, credentials):
        return AuthorizedSession(credentials, refresh_timeout=10, max_refresh_attempts=1)

    def _get(self, session, path: str, params: dict | None = None):
        try:
            response = session.get(f"https://gmail.googleapis.com/gmail/v1/users/me/{path}", params=params, timeout=10)
            if response.status_code == 401:
                raise GmailError("reconnect_required", 401)
            if response.status_code == 403:
                raise GmailError("access_denied", 403)
            if response.status_code == 404:
                raise GmailError("message_not_found", 404)
            if response.status_code == 429:
                raise GmailError("rate_limited", 429)
            if not response.ok:
                raise GmailError("gmail_unavailable")
            return response.json()
        except TransportError:
            raise GmailError("gmail_unavailable") from None
        except GoogleAuthError:
            raise GmailError("reconnect_required", 401) from None
        except (requests.RequestException, ValueError):
            raise GmailError("gmail_unavailable") from None

    def list_messages(self, credentials, query: str, page_token: str | None):
        params = {"maxResults": 10, "q": query, "includeSpamTrash": "false"}
        if page_token:
            params["pageToken"] = page_token
        with self._session(credentials) as session:
            page = self._get(session, "messages", params)
            messages = []
            for item in page.get("messages", []):
                try:
                    message = self._get(session, f"messages/{item['id']}", {
                        "format": "metadata", "metadataHeaders": ["Subject", "From"],
                    })
                    messages.append(email_from_message(message)["email"])
                except GmailError as error:
                    if error.status != 404:
                        raise
            return {"messages": messages, "next_page_token": page.get("nextPageToken")}

    def get_message(self, credentials, message_id: str):
        with self._session(credentials) as session:
            return email_from_message(self._get(session, f"messages/{message_id}", {"format": "full"}), full=True)

    def revoke(self, credentials) -> bool:
        try:
            response = requests.post("https://oauth2.googleapis.com/revoke", data={
                "token": credentials.refresh_token or credentials.token,
            }, timeout=10)
            return response.status_code == 200
        except requests.RequestException:
            return False
