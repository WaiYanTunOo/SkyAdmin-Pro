"""Desktop Google OAuth (stdlib urllib + local redirect + PKCE)."""

from __future__ import annotations

import secrets
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

from skyadmin_pro.services.drive.errors import NotConfiguredError
from skyadmin_pro.services.drive.oauth_pkce import exchange_code, pkce_pair
from skyadmin_pro.services.drive.tokens import (
    resolve_client_id,
    resolve_client_secret,
    save_refresh_token,
)

AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
SCOPES = "https://www.googleapis.com/auth/drive.file"


def connect_google_drive(db, *, timeout_sec: float = 180.0) -> str:
    """Open browser OAuth; store refresh token. Returns success message."""
    client_id = resolve_client_id(db)
    client_secret = resolve_client_secret(db)
    if not client_id:
        raise NotConfiguredError(
            "Google OAuth is not configured. Set GOOGLE_OAUTH_CLIENT_ID "
            "or paste the vendor Client ID into oauth_defaults."
        )

    state = secrets.token_urlsafe(16)
    code_verifier, code_challenge = pkce_pair()
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
            self.wfile.write(b"SkyAdmin: Authorization received. Return to the app to finish connecting.")

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
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
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
    tokens = exchange_code(client_id, client_secret, code, redirect_uri, code_verifier)
    refresh = (tokens.get("refresh_token") or "").strip()
    if not refresh:
        raise NotConfiguredError("No refresh_token returned — revoke app access and retry.")
    save_refresh_token(db, refresh)
    return "Google Drive connected."
