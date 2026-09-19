"""Encrypted OAuth token storage for customer Drive."""

from __future__ import annotations

import os

from skyadmin_pro.services.drive.keys import (
    SETTING_DRIVE_CLIENT_ID,
    SETTING_DRIVE_CLIENT_SECRET,
    SETTING_DRIVE_REFRESH_TOKEN,
)
from skyadmin_pro.services.secret_fields import decrypt_secret, encrypt_secret


def resolve_client_id(db=None) -> str:
    env = (os.environ.get("GOOGLE_OAUTH_CLIENT_ID") or "").strip()
    if env:
        return env
    if db is not None:
        return (db.get_setting(SETTING_DRIVE_CLIENT_ID) or "").strip()
    return ""


def resolve_client_secret(db=None) -> str:
    env = (os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET") or "").strip()
    if env:
        return env
    if db is None:
        return ""
    raw = (db.get_setting(SETTING_DRIVE_CLIENT_SECRET) or "").strip()
    return decrypt_secret(raw) if raw else ""


def save_refresh_token(db, token: str) -> None:
    db.set_setting(SETTING_DRIVE_REFRESH_TOKEN, encrypt_secret(token or ""))


def load_refresh_token(db) -> str:
    raw = (db.get_setting(SETTING_DRIVE_REFRESH_TOKEN) or "").strip()
    return decrypt_secret(raw) if raw else ""


def clear_drive_tokens(db) -> None:
    db.set_setting(SETTING_DRIVE_REFRESH_TOKEN, "")


def save_client_config(db, client_id: str, client_secret: str = "") -> None:
    db.set_setting(SETTING_DRIVE_CLIENT_ID, (client_id or "").strip())
    if client_secret:
        db.set_setting(SETTING_DRIVE_CLIENT_SECRET, encrypt_secret(client_secret))
