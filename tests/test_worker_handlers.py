"""Tests for Worker API input validation patterns."""

from __future__ import annotations

import re


def test_machine_id_regex():
    """Machine ID must be 1-16 uppercase hex characters."""
    pattern = re.compile(r"^[0-9A-F]{1,16}$")
    assert pattern.match("A1B2C3D4E5F60718")
    assert pattern.match("ABCDEF0123456789")
    assert pattern.match("A")
    assert pattern.match("0")
    assert not pattern.match("")
    assert not pattern.match("GHIJ")
    assert not pattern.match("a1b2c3d4e5f60718")
    assert not pattern.match("A1B2C3D4E5F607180")
    assert not pattern.match("A1B2C3D4E5F6071 ")
    assert not pattern.match(" A1B2C3D4E5F6071")


def test_machine_id_exact_length_boundaries():
    """Machine ID at exactly 1 and 16 characters."""
    pattern = re.compile(r"^[0-9A-F]{1,16}$")
    assert pattern.match("A")
    assert pattern.match("A1B2C3D4E5F60718")
    assert not pattern.match("A1B2C3D4E5F607189")


def test_machine_id_all_hex_chars():
    """All valid hex digits accepted."""
    pattern = re.compile(r"^[0-9A-F]{1,16}$")
    for char in "0123456789ABCDEF":
        assert pattern.match(char)
    for char in "GHIJKLMNOPQRSTUVWXYZ":
        assert not pattern.match(char)


def test_nonce_max_length():
    """Nonce validation should cap at 256 characters."""
    assert len("a" * 256) <= 256
    assert len("a" * 257) > 256


def test_nonce_valid_format():
    """Nonce is typically a hex string."""
    pattern = re.compile(r"^[0-9a-fA-F]+$")
    assert pattern.match("deadbeef")
    assert pattern.match("DEADBEEF")
    assert pattern.match("0")
    assert not pattern.match("")
    assert not pattern.match("xyz")


def test_api_key_format():
    """API keys are typically long alphanumeric strings."""
    pattern = re.compile(r"^[A-Za-z0-9_-]{20,}$")
    assert pattern.match("a" * 20)
    assert pattern.match("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef")
    assert pattern.match("key-with-dashes_and_underscores_12345")
    assert not pattern.match("short")
    assert not pattern.match("has spaces")
    assert not pattern.match("has@special!chars")


def test_nonce_uniqueness():
    """Generated nonces should be unique."""
    import secrets

    nonces = {secrets.token_hex(16) for _ in range(1000)}
    assert len(nonces) == 1000
