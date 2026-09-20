"""Desktop Google OAuth (stdlib urllib + local redirect)."""

from __future__ import annotations

import json
import secrets
import threading
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

from skyadmin_pro.services.drive.errors import NotConfiguredError
from skyadmin_pro.services.drive.tokens import (
    resolve_client_id,
    resolve_client_secret,
    save_refresh_token,
)

AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"
SCOPES = "https://www.googleapis.com/auth/drive.file"


def _exchange_code(client_id: str, client_secret: str, code: str, redirect_uri: str) -> dict:
    data = urllib.parse.urlencode(
        {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
    ).encode()
    req = urllib.request.Request(TOKEN_URI, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:  # nosec B310 - fixed https TOKEN_URI
        return json.loads(resp.read().decode())


def connect_google_drive(db, *, timeout_sec: float = 180.0) -> str:
    """Open browser OAuth; store refresh token. Returns success message."""
    client_id = resolve_client_id(db)
    client_secret = resolve_client_secret(db)
    if not client_id or not client_secret:
        raise NotConfiguredError(
            "Set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET (or Settings client id/secret) first."
        )

    state = secrets.token_urlsafe(16)
    result: dict = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if qs.get("state", [""])[0] != state:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Invalid state")
                return
            result["code"] = qs.get("code", [""])[0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"SkyAdmin: Google Drive connected. You can close this tab.")

        def log_message(self, *_args):
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    redirect_uri = f"http://127.0.0.1:{port}/"
    params = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": SCOPES,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
    )
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    webbrowser.open(f"{AUTH_URI}?{params}")
    thread.join(timeout=timeout_sec)
    server.server_close()
    code = result.get("code") or ""
    if not code:
        raise NotConfiguredError("OAuth timed out or was cancelled.")
    tokens = _exchange_code(client_id, client_secret, code, redirect_uri)
    refresh = (tokens.get("refresh_token") or "").strip()
    if not refresh:
        raise NotConfiguredError("No refresh_token returned — revoke app access and retry.")
    save_refresh_token(db, refresh)
    return "Google Drive connected."
