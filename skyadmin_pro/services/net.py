"""Outbound HTTP policy — fail closed on TLS downgrade and SSRF."""

from __future__ import annotations

import ipaddress
import os
import socket
from urllib.parse import urlparse

#: Escape hatch for local dev only (never set in production builds).
_ALLOW_HTTP_ENV = "SKYADMIN_ALLOW_HTTP_API"
_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
_METADATA_HOSTS = frozenset(
    {
        "metadata",
        "metadata.google.internal",
        "metadata.goog",
        "kubernetes.default",
        "kubernetes.default.svc",
    }
)


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
    if scheme == "http" and (host in _LOCAL_HOSTS or os.environ.get(_ALLOW_HTTP_ENV) == "1"):
        return url
    raise RuntimeError(
        f"Refusing insecure API URL ({scheme or '?'}://{host or '?'}). "
        "API_BASE_URL must use https:// — "
        f"set {_ALLOW_HTTP_ENV}=1 only for local development."
    )


def assert_public_https_url(url: str, *, resolve: bool = True) -> str:
    """Return url if https to a non-private host; raise ValueError otherwise.

    When resolve=False, IP literals and metadata names are still rejected;
    hostname DNS checks are deferred (for construct-time / offline tests).
    """
    raw = (url or "").strip()
    try:
        parts = urlparse(raw)
    except ValueError as exc:
        raise ValueError("invalid URL") from exc
    if (parts.scheme or "").lower() != "https" or not parts.hostname:
        raise ValueError("URL must be https with a host")
    assert_public_host(parts.hostname, resolve=resolve)
    return raw


def assert_public_host(hostname: str, *, resolve: bool = True) -> None:
    """Raise ValueError if host is private, loopback, link-local, or metadata."""
    host = (hostname or "").strip().lower().rstrip(".")
    if not host or host in _LOCAL_HOSTS or host in _METADATA_HOSTS or host.endswith(".localhost"):
        raise ValueError("host not allowed")
    try:
        addr: ipaddress.IPv4Address | ipaddress.IPv6Address | None = ipaddress.ip_address(host)
    except ValueError:
        addr = None
    if addr is not None:
        if _is_non_public_ip(addr):
            raise ValueError("host not allowed")
        return
    if not resolve:
        return
    try:
        infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise ValueError("host not resolvable") from exc
    if not infos:
        raise ValueError("host not resolvable")
    for info in infos:
        if _is_non_public_ip(ipaddress.ip_address(info[4][0])):
            raise ValueError("host not allowed")


def _is_non_public_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return bool(
        ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified
    )
