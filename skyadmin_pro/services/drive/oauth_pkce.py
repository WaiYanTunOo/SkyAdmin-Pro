"""PKCE helpers + token code exchange for Google OAuth."""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import urllib.error
import urllib.parse
import urllib.request

from skyadmin_pro.services.drive.errors import NotConfiguredError

TOKEN_URI = "https://oauth2.googleapis.com/token"


def pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def _redact(text: str, secret: str) -> str:
    if secret and secret in text:
        return text.replace(secret, "[redacted]")
    return text


def exchange_code(
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
    code_verifier: str,
) -> dict:
    payload = {
        "code": code,
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
        "code_verifier": code_verifier,
    }
    if client_secret:
        payload["client_secret"] = client_secret
    data = urllib.parse.urlencode(payload).encode()
    req = urllib.request.Request(TOKEN_URI, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:  # nosec B310 - fixed https TOKEN_URI
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode(errors="replace")
        try:
            err = json.loads(raw)
            detail = err.get("error_description") or err.get("error") or raw
        except json.JSONDecodeError:
            detail = raw or str(exc)
        detail = _redact(str(detail), client_secret)
        hint = ""
        if "invalid_client" in detail.lower() or exc.code in (401, 400):
            hint = " Paste the OAuth Client secret under Advanced → Save client, then retry."
        raise NotConfiguredError(f"Google token exchange failed: {detail}.{hint}") from None
