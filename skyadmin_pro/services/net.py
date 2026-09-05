"""Outbound HTTP policy — fail closed on TLS downgrade.

Every Worker request must go over HTTPS. A tampered config pointing
API_BASE_URL at plain http:// would leak activation codes, sync tokens,
and Bearer credentials, and let a MITM suppress revocation lists.
"""

from __future__ import annotations

import os
from urllib.parse import urlparse

#: Escape hatch for local dev only (never set in production builds).
_ALLOW_HTTP_ENV = "SKYADMIN_ALLOW_HTTP_API"
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def require_https_api_url(api_url: str) -> str:
    """Return the stripped URL, or raise RuntimeError on TLS downgrade.

    Allows http:// only for loopback hosts or when SKYADMIN_ALLOW_HTTP_API=1.
    """
    url = (api_url or "").strip()
    if not url:
        raise RuntimeError("API_BASE_URL is not configured.")
    try:
        parts = urlparse(url if "://" in url else f"https://{url}")
    except ValueError as exc:
        raise RuntimeError(f"API_BASE_URL is not a valid URL: {url!r}") from exc
    scheme = (parts.scheme or "").lower()
    host = (parts.hostname or "").lower()
    if scheme == "https":
        return url
    if scheme == "http" and (
        host in _LOCAL_HOSTS or os.environ.get(_ALLOW_HTTP_ENV) == "1"
    ):
        return url
    raise RuntimeError(
        f"Refusing insecure API URL ({scheme or '?'}://{host or '?'}). "
        "API_BASE_URL must use https:// — "
        f"set {_ALLOW_HTTP_ENV}=1 only for local development."
    )
