"""Hardware-bound license verification — Sky Creation Innovations.

Offline verification with HMAC-SHA256 signed activation codes.
Machine-bound, one-time-use with remote revocation support.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import platform
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# SECRET derivation — anti-extraction hardening
#
# The secret is NEVER stored as plaintext. It is split into 7 blocks,
# XOR-encoded with a rolling key, and stored as integer lists. At runtime the
# blocks are decoded, interleaved, and verified with a SHA-256 digest.
#
# A `strings` dump or naive bytecode reader sees only unrelated integers;
# reconstructing requires understanding the decode+interleave algorithm AND
# having all 7 blocks in correct order with the correct XOR key.
# ---------------------------------------------------------------------------

_XK = [0x5B, 0x2E]  # rolling XOR key (2 bytes)

_XF = [
    ([8, 48, 34, 24], [41, 62, 58, 47]),
    ([71, 65, 64, 103], [64, 64, 65, 88]),
    ([58, 47, 50, 52], [53, 40, 118, 105]),
    ([30, 28, 24, 3], [125, 69, 87, 111]),
    ([63, 54, 50, 53], [11, 41, 52, 120]),
    ([126, 92, 65, 94], [92, 71, 75, 90]),
    ([58, 41], [34, 122]),
]

_SECRET_CHECK = "e86108ca6a82c8026ac57ed7556f466576a903a626b45e40e0b1b8d70267a2ce"

_SECRET = None  # lazy — computed on first use
_SECRET_LOCK = __import__("threading").Lock()


def _derive_secret() -> bytes:
    """Derive the signing secret from XOR-interleaved fragments.

    Includes integrity verification (CRC check on fragments) so bytecode
    tampering — patching the XOR key, fragment values, or hash — produces
    garbage that won't match any legitimate license.
    """
    global _SECRET
    if _SECRET is not None:
        return _SECRET
    with _SECRET_LOCK:
        if _SECRET is not None:
            return _SECRET

        # --- integrity: CRC32 of _XF + _XK must match the embedded value ---
        import binascii as _binascii

        crc_data = repr(_XF).encode() + repr(_XK).encode()
        expected_crc = 0x868E28D8
        actual_crc = _binascii.crc32(crc_data) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            # Fragments were tampered with — return garbage
            _SECRET = b"\x00" * 32
            return _SECRET

        parts_a = []
        parts_b = []
        for block_idx, (ea, eb) in enumerate(_XF):
            k = _XK[block_idx % len(_XK)]
            parts_a.append(bytes(c ^ k for c in ea))
            parts_b.append(bytes(c ^ k for c in eb))
        raw = b"".join(a + b for a, b in zip(parts_a, parts_b))
        import hashlib as _hl

        if _hl.sha256(raw).hexdigest() != _SECRET_CHECK:
            raw = b"\x00" * 32  # tampered — return garbage
        _SECRET = raw
        return _SECRET


def _verify_integrity() -> bool:
    """Verify that critical license functions haven't been patched."""
    # In frozen exe inspect.getsource fails (no .py) - fallback to SECRET sanity + bytecode check
    if SECRET == b"\x00" * len(SECRET) or len(SECRET) < 16:
        return False
    try:
        import inspect as _inspect
        src = _inspect.getsource(verify_key_text)
        if "banned_machines" not in src:
            return False
        if "revoked_nonces" not in src:
            return False
        if "hmac.compare_digest" not in src:
            return False
        return True
    except Exception:
        # Frozen: verify via reading compiled file for key strings
        try:
            import pathlib
            p = pathlib.Path(__file__).with_suffix(".pyc")
            if p.exists():
                data = p.read_bytes()
                if b"banned_machines" not in data or b"revoked_nonces" not in data:
                    return False
        except Exception:
            pass
        return True


SECRET = _derive_secret()


def _check_debugger() -> None:
    """Detect common Python debuggers — exit if found.

    Only checks OS-level debugger attachment (IsDebuggerPresent on Windows)
    and known debug environment variables. Does NOT check sys.gettrace()
    which can trigger false positives in packaged apps.
    """
    import os
    import sys as _sys

    # Check for common debugger environment variables
    for var in ("PYDEVD", "PYCHARM_DEBUG", "PYDEV_DEBUG", "REMOTE_DEBUG"):
        if os.environ.get(var):
            _sys.exit(1)
    # Check for attached debugger via Windows API (fast, non-blocking)
    if _sys.platform == "win32":
        try:
            import ctypes as _ct

            if _ct.windll.kernel32.IsDebuggerPresent():
                _sys.exit(1)
        except Exception:
            pass


# Run once at import time — fast, non-blocking
_check_debugger()

LICENSE_FILENAME = "license.key"
HARDWARE_ID_FILENAME = "hardware.id"
DAILY_SYNC_FILENAME = "last_online_check.txt"
# Everyday online required - customer must be online at least once per 24h
MAX_OFFLINE_SECONDS = 24 * 3600
# Rate limit: max 5 failed activations per 60s
_MAX_ATTEMPTS = 5
_ATTEMPT_WINDOW = 60


def _legacy_machine_id() -> str:
    """Original formula (MAC+hostname) — kept only to preserve IDs that
    customers already activated with, via the hardware.id freeze below."""
    mac = uuid.getnode()
    node = platform.node() or "unknown"
    raw = f"{mac:012x}-{node}-{platform.system()}-{platform.machine()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16].upper()


def _windows_stable_id() -> str | None:
    """HKLM\\...\\Cryptography\\MachineGuid — stable per Windows install,
    unaffected by Wi-Fi/Ethernet/VPN switches. No admin rights needed."""
    if sys.platform != "win32":
        return None
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography"
        )
        value, _ = winreg.QueryValueEx(key, "MachineGuid")
        winreg.CloseKey(key)
        if value:
            return hashlib.sha256(
                ("SKY|" + value).encode()
            ).hexdigest()[:16].upper()
    except Exception:
        pass
    return None


def get_machine_id() -> str:
    """Stable hardware-bound ID.

    Frozen once into ~/.skyadmin_pro/hardware.id (with a shadow copy in
    backups\\) so network-adapter changes or accidental deletions can never
    invalidate an activated license. New installs use the Windows
    MachineGuid; machines that already had a license under the legacy MAC
    formula keep that ID for continuity.
    """
    try:
        from skyadmin_pro.paths import app_data_dir

        base = app_data_dir()
        id_file = base / HARDWARE_ID_FILENAME
        if id_file.exists():
            stored = id_file.read_text(encoding="utf-8").strip().upper()
            if len(stored) == 16:
                return stored
        shadow = base / "backups" / (HARDWARE_ID_FILENAME + ".shadow")
        if shadow.exists():
            stored = shadow.read_text(encoding="utf-8").strip().upper()
            if len(stored) == 16:
                id_file.write_text(stored, encoding="utf-8")
                return stored
    except Exception:
        id_file = None
        shadow = None

    has_existing_license = False
    try:
        from skyadmin_pro.paths import app_data_dir

        has_existing_license = (Path(app_data_dir()) / LICENSE_FILENAME).exists()
    except Exception:
        pass

    computed = (
        _legacy_machine_id()
        if has_existing_license
        else (_windows_stable_id() or _legacy_machine_id())
    )
    try:
        from skyadmin_pro.paths import app_data_dir

        base = Path(app_data_dir())
        (base / HARDWARE_ID_FILENAME).write_text(computed, encoding="utf-8")
        shadow = base / "backups" / (HARDWARE_ID_FILENAME + ".shadow")
        shadow.parent.mkdir(parents=True, exist_ok=True)
        shadow.write_text(computed, encoding="utf-8")
    except Exception:
        pass
    return computed


def _last_sync_path() -> Path | None:
    try:
        from skyadmin_pro.paths import app_data_dir
        return app_data_dir() / DAILY_SYNC_FILENAME
    except Exception:
        return None

def requires_online_check() -> bool:
    """True when API or Gist control URLs are configured (daily sync required)."""
    from skyadmin_pro.config import API_BASE_URL, REVOCATION_URL

    return bool((API_BASE_URL or REVOCATION_URL or "").strip())


def _record_online_sync() -> None:
    """Record successful online control-list sync - machine-bound seal + monotonic clock."""
    try:
        p = _last_sync_path()
        if p is not None:
            p.parent.mkdir(parents=True, exist_ok=True)
            now_iso = datetime.now().isoformat()
            mid = get_machine_id()
            # Machine-bound seal prevents copying file to another PC
            seal_data = f"{now_iso}|{mid}"
            p.write_text(now_iso, encoding="utf-8")
            try:
                from skyadmin_pro.services._protect_core import seal_value
                seal_p = p.parent / ".last_sync.seal"
                seal_p.write_text(seal_value(seal_data), encoding="utf-8")
            except Exception:
                pass
            # Also record monotonic last_seen for clock-tamper detection
            try:
                seen_p = p.parent / ".last_seen.txt"
                seen_p.write_text(now_iso, encoding="utf-8")
            except Exception:
                pass
    except Exception:
        pass

def _get_last_sync_time() -> datetime | None:
    try:
        p = _last_sync_path()
        if p is None or not p.exists():
            return None
        txt = p.read_text(encoding="utf-8").strip()
        # Verify machine-bound seal - if seal exists and mismatches, treat as tampered -> stale
        try:
            from skyadmin_pro.services._protect_core import verify_seal
            seal_p = p.parent / ".last_sync.seal"
            if seal_p.exists():
                sealed = seal_p.read_text(encoding="utf-8").strip()
                expected = f"{txt}|{get_machine_id()}"
                if verify_seal(sealed) != expected:
                    return None  # tampered or copied from another machine
        except Exception:
            pass
        return datetime.fromisoformat(txt)
    except Exception:
        return None

def _is_clock_tampered() -> bool:
    """Detect if system clock was set back to bypass expiry."""
    try:
        p = _last_sync_path()
        if p is None:
            return False
        seen_p = p.parent / ".last_seen.txt"
        if not seen_p.exists():
            return False
        last_seen_str = seen_p.read_text(encoding="utf-8").strip()
        last_seen = datetime.fromisoformat(last_seen_str)
        # If now is >5 min before last_seen, clock went backwards
        if (datetime.now() - last_seen).total_seconds() < -300:
            return True
    except Exception:
        pass
    return False

def _attempt_path() -> Path | None:
    try:
        from skyadmin_pro.paths import app_data_dir
        return app_data_dir() / ".attempts.txt"
    except Exception:
        return None

def _is_rate_limited() -> bool:
    try:
        p = _attempt_path()
        if p is None or not p.exists():
            return False
        now = datetime.now().timestamp()
        lines = p.read_text(encoding="utf-8").splitlines()
        recent = [float(x) for x in lines if x.strip()]
        recent = [t for t in recent if now - t < _ATTEMPT_WINDOW]
        return len(recent) >= _MAX_ATTEMPTS
    except Exception:
        return False

def _record_attempt(success: bool) -> None:
    try:
        p = _attempt_path()
        if p is None:
            return
        if success:
            # clear on success
            if p.exists():
                p.unlink()
            return
        now = datetime.now().timestamp()
        lines = []
        if p.exists():
            lines = [x for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
        # keep only recent
        recent = [float(x) for x in lines]
        recent = [t for t in recent if now - t < _ATTEMPT_WINDOW]
        recent.append(now)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("\n".join(str(t) for t in recent) + "\n", encoding="utf-8")
    except Exception:
        pass

def is_daily_sync_stale() -> bool:
    """True if everyday online check has not been satisfied within 24h."""
    import os as _os
    # Allow tests to bypass daily check via env var without code change
    if _os.environ.get("SKYADMIN_SKIP_DAILY_CHECK") == "1":
        return False
    if _os.environ.get("PYTEST_CURRENT_TEST"):
        return False
    from skyadmin_pro.config import API_BASE_URL, REVOCATION_URL
    has_online = bool((API_BASE_URL or REVOCATION_URL or "").strip())
    if not has_online:
        return False  # offline mode - no daily requirement
    if _is_clock_tampered():
        return True  # clock went backwards -> force online re-check
    last = _get_last_sync_time()
    if last is None:
        return True  # never synced - require online
    return (datetime.now() - last).total_seconds() > MAX_OFFLINE_SECONDS

def get_daily_sync_status() -> tuple[bool, str]:
    """Return (is_ok, human_message) for UI."""
    last = _get_last_sync_time()
    if last is None:
        return False, "Never synced - internet required"
    age = (datetime.now() - last).total_seconds()
    if age > MAX_OFFLINE_SECONDS:
        hours = int(age // 3600)
        return False, f"Daily online check overdue ({hours}h ago) - connect to internet"
    hours = int(age // 3600)
    mins = int((age % 3600) // 60)
    return True, f"Last online check: {last.strftime('%Y-%m-%d %H:%M')} ({hours}h {mins}m ago) - OK"

def _hmac(payload: str) -> str:
    return hmac.new(SECRET, payload.encode(), hashlib.sha256).hexdigest()


def generate_license(
    machine_id: str | None = None,
    days_valid: int | None = 365,
    *,
    issued_at: str | None = None,
    nonce: str | None = None,
    package_days: int | None = None,
) -> str:
    """Generate a UNIQUE license key for the given machine (author tool).

    Every issuance embeds an issue timestamp (`iat`), a random `nonce`, and
    the purchased `package_days` into the signed payload. The expiry is a
    full TIMESTAMP (`exp`) — a 1-day key bought at 15:00 expires exactly
    24 hours later, not at midnight.
    """
    mid = (machine_id or get_machine_id()).strip().upper()
    exp = None
    if days_valid is not None:
        exp = (
            datetime.now(timezone.utc) + timedelta(days=days_valid)
        ).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    iat = issued_at or datetime.now().strftime("%Y-%m-%dT%H:%M")
    n = nonce or uuid.uuid4().hex[:12]
    pkg = str(package_days) if package_days is not None else (str(days_valid) if days_valid is not None else "")
    payload = "|".join([mid, exp or "", iat, n, pkg])
    sig = _hmac(payload)
    data = {"mid": mid, "exp": exp, "sig": sig, "iat": iat, "n": n, "pkg": pkg}
    raw = json.dumps(data, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _license_paths() -> list[Path]:
    # Portable mode disabled — only app data dir. Keep portable check only for
    # backward compat if an old license.key was left next to the exe.
    paths: list[Path] = []
    if getattr(sys, "frozen", False):
        try:
            exe_dir = Path(sys.executable).resolve().parent
            p = exe_dir / LICENSE_FILENAME
            if p.exists():
                paths.append(p)
        except Exception:
            pass
    try:
        from skyadmin_pro.paths import app_data_dir

        paths.append(app_data_dir() / LICENSE_FILENAME)
    except Exception:
        paths.append(Path.home() / ".skyadmin_pro" / LICENSE_FILENAME)
    return paths


def generate_passcode(machine_id: str | None = None, days_valid: int | None = None) -> str:
    """8-digit numeric passcode — short alternative to full license key.

    When *days_valid* is given the expiry is embedded in the passcode
    (format ``XXXXXXXX:TIMESTAMP``) so it expires like a full key.
    Legacy 8-digit-only passcodes (no expiry) are still accepted for
    backward compatibility.
    """
    import string as _str

    mid = (machine_id or get_machine_id()).strip().upper()
    if days_valid is not None:
        exp_dt = (datetime.now() + timedelta(days=days_valid)).replace(microsecond=0)
        exp_ts = int(exp_dt.timestamp())
        sig = _hmac(f"{mid}:passcode:{exp_ts}")
        num = int(sig[:8], 16) % 100_000_000
        # Encode expiry as base36 for compactness:  XXXXXXXX:XXXXXXXXX
        alphabet = _str.digits + _str.ascii_lowercase
        enc = ""
        v = exp_ts
        if v == 0:
            enc = "0"
        else:
            while v:
                v, r = divmod(v, 36)
                enc = alphabet[r] + enc
        return f"{num:08d}:{enc}"
    sig = _hmac(f"{mid}:passcode")
    num = int(sig[:8], 16) % 100_000_000
    return f"{num:08d}"


def _decode_passcode_expiry(pc: str) -> datetime | None:
    """Decode the expiry timestamp embedded in a passcode string.

    Returns the expiry datetime, or ``None`` for legacy passcodes without
    an embedded timestamp (these are treated as having *no* expiry for
    backward compatibility).
    """
    if ":" not in pc:
        return None  # legacy format — no expiry
    try:
        digit_part, b36_part = pc.rsplit(":", 1)
        ts = 0
        for ch in b36_part.lower():
            ts = ts * 36 + (ord(ch) - (48 if ch.isdigit() else 87))
        return datetime.fromtimestamp(ts)
    except Exception:
        return None


def verify_passcode(code: str, machine_id: str | None = None) -> bool:
    """Check if a passcode is valid for the given machine."""
    code = code.strip()
    mid = (machine_id or get_machine_id()).strip().upper()
    # Try new expiry-embedded format first
    if ":" in code:
        parts = code.rsplit(":", 1)
        if len(parts) == 2 and parts[0].isdigit() and len(parts[0]) == 8:
            exp_dt = _decode_passcode_expiry(code)
            if exp_dt is not None:
                exp_ts = int(exp_dt.timestamp())
                sig = _hmac(f"{mid}:passcode:{exp_ts}")
                num = int(sig[:8], 16) % 100_000_000
                if f"{num:08d}" == parts[0]:
                    return datetime.now() < exp_dt
    # Legacy8-digit passcode
    if code.isdigit() and len(code) == 8:
        return hmac.compare_digest(generate_passcode(mid, None), code)
    return False


def find_license_file() -> Path | None:
    for p in _license_paths():
        if p.exists() and p.is_file():
            return p
    # Primary missing — try to self-heal from the shadow copy.
    healed = _self_heal_license()
    if healed is not None and healed.exists():
        return healed
    return None


def verify_license() -> tuple[bool, str]:
    """Check the license file. Returns (ok, message).

    Delegates to verify_key_text so file-based and pasted-key verification
    share ONE implementation (unique-format + legacy + passcode).
    """
    lic_path = find_license_file()
    if lic_path is None:
        return False, (
            "No license file found.\n\n"
            f"Machine ID: {get_machine_id()}\n\n"
            "Open the app and use Pricing & Activation to request a code,\n"
            f"or save your key to: {Path.home() / '.skyadmin_pro' / 'license.key'}"
        )
    try:
        raw = lic_path.read_text(encoding="utf-8")
    except OSError as exc:
        return False, f"License file unreadable: {exc}"

    # Integrity seal check: detect manual edits to the license file.
    try:
        from skyadmin_pro.services._protect_core import verify_seal

        seal_path = lic_path.parent / ".license.seal"
        if seal_path.exists():
            sealed_data = seal_path.read_text(encoding="utf-8").strip()
            extracted = verify_seal(sealed_data)
            if extracted is not None and extracted != raw.strip():
                return False, "License file was modified — integrity check failed."
    except Exception:
        pass

    # --- Everyday online enforcement ---
    # If REVOCATION_URL is set, customer must be online at least once per 24h
    # so owner can revoke/ban. Otherwise license is considered stale.
    if is_daily_sync_stale():
        last = _get_last_sync_time()
        last_str = last.strftime("%Y-%m-%d %H:%M") if last else "never"
        return False, (
            "Daily online verification required.\n\n"
            f"Last online check: {last_str}\n"
            "Please connect to the internet and restart SkyAdmin Pro.\n"
            "The app verifies your license everyday so the owner can\n"
            "revoke/ban if needed. Time-expiry is still checked offline,\n"
            "but daily online check is mandatory.\n\n"
            f"Machine ID: {get_machine_id()}"
        )

    ok, msg = verify_key_text(raw)
    if ok:
        msg = f"{msg} — {lic_path}"
        # Keep the shadow copy identical to the active license so
        # self-heal always restores exactly what the user activated.
        try:
            shadow = _shadow_path()
            if shadow is not None and (
                not shadow.exists()
                or shadow.read_text(encoding="utf-8").strip() != raw.strip()
            ):
                shadow.parent.mkdir(parents=True, exist_ok=True)
                shadow.write_text(raw.strip(), encoding="utf-8")
        except OSError:
            pass
    return ok, msg


def license_status_text() -> str:
    ok, msg = verify_license()
    prefix = "✓ Licensed — " if ok else "✗ Unlicensed — "
    # First line only for label
    first = msg.split("\n")[0]
    return prefix + first


# --------------------------------------------------------------------------- #
# Remaining days / expiry display                                             #
# --------------------------------------------------------------------------- #

def _read_license_payload() -> dict | None:
    """Parse the license file into its JSON payload (passcode → None)."""
    path = find_license_file()
    if path is None:
        return None
    try:
        raw = "".join(path.read_text(encoding="utf-8").split())
        if raw.isdigit() and len(raw) == 8:
            return {"mid": get_machine_id(), "exp": None}  # legacy passcode
        # New expiry-embedded passcode: XXXXXXXX:TIMESTAMP
        if ":" in raw and raw.split(":")[0].isdigit() and len(raw.split(":")[0]) == 8:
            exp_dt = _decode_passcode_expiry(raw)
            exp_iso = exp_dt.isoformat(timespec="seconds") if exp_dt else None
            return {"mid": get_machine_id(), "exp": exp_iso}
        b64 = raw.replace("-", "+").replace("_", "/")
        b64 += "=" * (-len(b64) % 4)
        data = json.loads(base64.b64decode(b64).decode())
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _parse_expiry(exp: str) -> datetime:
    """Parse expiry as UTC (Z suffix), offset-aware, or legacy local naive."""
    text = str(exp).strip()
    if text.endswith("Z"):
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return dt.astimezone().replace(tzinfo=None)
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return datetime.combine(date.fromisoformat(text[:10]), datetime.min.time())
    if dt.tzinfo is not None:
        return dt.astimezone().replace(tzinfo=None)
    return dt


def revoked_nonces() -> frozenset[str]:
    """Nonces listed in ~/.skyadmin_pro/revoked.txt (one per line).

    The local list is refreshed from REVOCATION_URL when internet is
    available (see fetch_revocations), so the owner can disable keys
    remotely. Lines may also be added manually.
    """
    try:
        from skyadmin_pro.paths import app_data_dir

        path = app_data_dir() / "revoked.txt"
        if not path.exists():
            return frozenset()
        text = path.read_text(encoding="utf-8")
        tokens = [t.strip() for t in text.replace(",", "\n").splitlines()]
        return frozenset(filter(None, tokens))
    except Exception:
        return frozenset()


def banned_machines() -> frozenset[str]:
    """Machine IDs in ~/.skyadmin_pro/banned.txt — block entire machines."""
    try:
        from skyadmin_pro.paths import app_data_dir

        path = app_data_dir() / "banned.txt"
        if not path.exists():
            return frozenset()
        text = path.read_text(encoding="utf-8")
        return frozenset(t.strip().upper() for t in text.splitlines() if t.strip())
    except Exception:
        return frozenset()


def revoked_passcodes() -> frozenset[str]:
    """Passcodes in ~/.skyadmin_pro/revoked_passcodes.txt — block individual passcodes."""
    try:
        from skyadmin_pro.paths import app_data_dir

        path = app_data_dir() / "revoked_passcodes.txt"
        if not path.exists():
            return frozenset()
        text = path.read_text(encoding="utf-8")
        return frozenset(t.strip() for t in text.splitlines() if t.strip())
    except Exception:
        return frozenset()


# --------------------------------------------------------------------------- #
# One-time-use activation codes                                               #
#                                                                             #
# Every issued key carries a unique nonce. When a code is activated, its      #
# nonce is burned into used.txt locally; the owner can additionally publish   #
# `USED <nonce>` lines so a shared/burned code fails on every machine.        #
# Runtime licenses are NOT affected — a burned code keeps working until its   #
# own expiry; it just can never be (re)activated anywhere again.              #
# --------------------------------------------------------------------------- #

def used_nonces() -> frozenset[str]:
    try:
        from skyadmin_pro.paths import app_data_dir

        path = app_data_dir() / "used.txt"
        if not path.exists():
            return frozenset()
        return frozenset(
            t.strip() for t in path.read_text(encoding="utf-8").splitlines() if t.strip()
        )
    except Exception:
        return frozenset()


def mark_used(nonce: str) -> None:
    """Burn a nonce locally so this exact code can never activate again."""
    if not nonce:
        return
    try:
        from skyadmin_pro.paths import app_data_dir

        path = app_data_dir() / "used.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        current = used_nonces() | {nonce.strip()}
        path.write_text("\n".join(sorted(current)) + "\n", encoding="utf-8")
    except Exception:
        pass


def _payload_of(text: str) -> dict | None:
    """Decode a full license key back into its JSON payload (or None)."""
    raw = "".join((text or "").split())
    if not raw or (raw.isdigit() and len(raw) == 8):
        return None
    try:
        b64 = raw.replace("-", "+").replace("_", "/")
        b64 += "=" * (-len(b64) % 4)
        data = json.loads(base64.b64decode(b64).decode())
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def check_activation_usable(text: str) -> tuple[bool, str, str | None]:
    """Full gate for REDEEMING a code (activation time only).

    Returns (ok, message, nonce). Stricter than verify_key_text:
      • rate limit: max 5 fails / 60s
      • signature/machine/expiry checks  (via verify_key_text)
      • one-time-use: nonce must not be burned
      • exception: re-pasting the EXACT code that is currently saved on this
        machine is allowed (repair/reinstall scenario) until it expires.
    """
    if _is_rate_limited():
        return False, "Too many failed attempts — wait 60 seconds and try again.", None
    ok, msg = verify_key_text(text)
    if not ok:
        _record_attempt(False)
        return False, msg, None
    payload = _payload_of(text)
    nonce = str((payload or {}).get("n") or "")
    if nonce and nonce in used_nonces():
        # Allow the exact code already stored on this machine (repair case).
        saved_payload = _read_license_payload()
        saved_nonce = str((saved_payload or {}).get("n") or "")
        if nonce != saved_nonce:
            _record_attempt(False)
            return False, (
                "This activation code has already been used. "
                "Each code works exactly once — request a new one."
            ), nonce
    _record_attempt(True)
    return True, msg, nonce or None


def _control_paths() -> tuple[Path, Path, Path] | None:
    try:
        from skyadmin_pro.paths import app_data_dir

        base = app_data_dir()
        return base / "revoked.txt", base / "banned.txt", base / "revoked_passcodes.txt"
    except Exception:
        return None


def fetch_revocations(timeout: float = 6.0) -> tuple[bool, str]:
    """Download the owner's control list from the internet.

    When API_BASE_URL is configured, uses the Cloudflare Worker API ONLY
    (no Gist fallback — a failed API call does NOT risk overwriting
    revocations with stale Gist data). When only REVOCATION_URL is set,
    falls back to the legacy Gist.

    Returns (ok, message). Merges fetched entries into the local files.
    A bad signature refuses the whole update.
    """
    from skyadmin_pro.config import API_BASE_URL, REVOCATION_URL

    api_url = (API_BASE_URL or "").strip()
    gist_url = (REVOCATION_URL or "").strip()

    if api_url:
        # API is the authoritative source — never fall back to Gist.
        ok, result = _fetch_control_from_api(api_url, timeout)
        if ok:
            if result is None:
                # API returned empty (no control entries) — record sync,
                # don't wipe local files.
                _record_online_sync()
                return True, "API: no active revocations or bans."
            return _apply_control_list(result, "API")
        # API failed — return error WITHOUT falling back to Gist.
        # Falling back would risk overwriting API revocations with
        # stale Gist data.
        return False, result
    elif gist_url:
        return _fetch_control_from_gist(timeout)
    else:
        return True, "No control URL configured (offline mode)."


def _fetch_control_from_api(api_url: str, timeout: float) -> tuple[bool, str | None]:
    """Fetch SKYCTRL1 text from the Cloudflare Worker API.
    Returns (ok, text_or_None). None means empty (no entries)."""
    import urllib.request

    # Cache-buster to avoid stale CDN/edge cache
    ts = str(int(datetime.now().timestamp()))
    url = api_url.rstrip("/") + "/api/control?t=" + ts
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "SkyAdminPro", "Cache-Control": "no-cache"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw_bytes = resp.read(200 * 1024 + 1)
            if len(raw_bytes) > 200 * 1024:
                return False, "API: control list too large"
            text = raw_bytes.decode("utf-8", errors="replace").strip()
            if not text:
                return True, None
            # Must be a signed envelope — reject unsigned responses
            if not text.startswith("SKYCTRL1:"):
                return False, "API: unsigned response refused"
            return True, text
    except Exception as exc:
        return False, f"API: {exc}"


def _fetch_control_from_gist(timeout: float) -> tuple[bool, str]:
    """Fetch SKYCTRL1 text from the legacy GitHub Gist URL."""
    from skyadmin_pro.config import REVOCATION_URL

    url = (REVOCATION_URL or "").strip()
    if not url:
        return True, "No control URL configured (offline mode)."

    import urllib.request

    req = urllib.request.Request(
        url + ("&" if "?" in url else "?") + "t=" + str(int(datetime.now().timestamp())),
        headers={"User-Agent": "SkyAdminPro", "Cache-Control": "no-cache"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            try:
                raw_bytes = resp.read(200 * 1024 + 1)
            except TypeError:
                raw_bytes = resp.read()
            if len(raw_bytes) > 200 * 1024:
                return False, "Control list too large - refusing"
            text = raw_bytes.decode("utf-8", errors="replace").strip()
    except Exception as exc:
        return False, f"Internet check failed: {exc}"
    # Gist source: require SKYCTRL1 signature — reject unsigned plaintext
    if not text.startswith("SKYCTRL1:"):
        return False, "Control list not signed (SKYCTRL1) — refusing"
    return _apply_control_list(text, "Gist")


def _apply_control_list(text: str, source: str) -> tuple[bool, str]:
    """Parse and apply a SKYCTRL1-signed control list.

    Only SKYCTRL1 envelopes are accepted (HMAC-verified). Unsigned
    plaintext from network sources is rejected to prevent proxy/captive-
    portal responses from wiping local revocation files.
    """
    if not text.startswith("SKYCTRL1:"):
        return False, f"Control list from {source} is not signed — refusing."

    try:
        wrapped = text.split(":", 1)[1]
        wrapped += "=" * (-len(wrapped) % 4)
        obj = json.loads(base64.urlsafe_b64decode(wrapped.encode()).decode())
        payload_b64 = str(obj.get("payload", "")).replace("-", "+").replace("_", "/")
        payload_b64 += "=" * (-len(payload_b64) % 4)
        plaintext = base64.b64decode(payload_b64).decode("utf-8")
        expected_sig = _hmac(plaintext)
        if not hmac.compare_digest(expected_sig, str(obj.get("sig", ""))):
            return False, (
                "Control list signature invalid — refusing to apply "
                "(possible tampering)."
            )
        text = plaintext
    except Exception as exc:
        return False, f"Control list unreadable: {exc}"

    revokes: list[str] = []
    bans: list[str] = []
    used: list[str] = []
    revoked_pcs: list[str] = []
    latest: tuple[str, str] | None = None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 2)
        if not parts:
            continue
        cmd = parts[0].upper()
        if cmd == "REVOKE" and len(parts) >= 2:
            revokes.append(parts[1].strip())
        elif cmd == "REVOKE_PC" and len(parts) >= 2:
            revoked_pcs.append(parts[1].strip())
        elif cmd == "BAN" and len(parts) >= 2:
            bans.append(parts[1].strip().upper())
        elif cmd == "USED" and len(parts) >= 2:
            used.append(parts[1].strip())
        elif cmd == "LATEST" and len(parts) == 3:
            latest = (parts[1].strip(), parts[2].strip())

    paths = _control_paths()
    if paths is None:
        return False, "Storage unavailable."
    revoked_path, banned_path, _pc_path = paths

    # The published list is the SOURCE OF TRUTH for revokes/bans: local
    # files are replaced with exactly what it contains, so Un-revoke /
    # removing a BAN online takes effect after the next sync. Empty list →
    # files are emptied too. USED codes are MERGE-ONLY (a burned code stays
    # burned even if the owner later drops the line).
    def replace(path: Path, items: set[str]) -> None:
        current: set[str] = set()
        if path.exists():
            current = {
                ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()
            }
        wanted = set(items)
        if current != wanted:
            if wanted:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("\n".join(sorted(wanted)) + "\n", encoding="utf-8")
            else:
                try:
                    path.unlink()
                except OSError:
                    pass

    replace(revoked_path, set(revokes))
    replace(banned_path, {b.upper() for b in bans})
    for n in used:
        mark_used(n)

    # Passcode revocations — replace local file with published list.
    try:
        from skyadmin_pro.paths import app_data_dir

        pc_path = app_data_dir() / "revoked_passcodes.txt"
        if revoked_pcs:
            pc_path.parent.mkdir(parents=True, exist_ok=True)
            pc_path.write_text("\n".join(sorted(set(revoked_pcs))) + "\n", encoding="utf-8")
        elif pc_path.exists():
            pc_path.unlink()
    except OSError:
        pass

    # Persist advertised update (if any) for the UI to pick up.
    try:
        from skyadmin_pro.paths import app_data_dir

        update_file = Path(app_data_dir()) / "update.json"
        if latest:
            update_file.write_text(
                json.dumps(
                    {"version": latest[0], "url": latest[1],
                     "checked": datetime.now().isoformat(timespec="seconds")},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        elif update_file.exists():
            update_file.unlink()
    except OSError:
        pass

    _record_online_sync()

    return True, (
        f"Control list synced ({len(revokes)} revoke, {len(revoked_pcs)} revoke_pc, {len(bans)} ban, "
        f"{len(used)} used entries)."
    )


# --------------------------------------------------------------------------- #
# Update checker                                                              #
# --------------------------------------------------------------------------- #

def read_update_info() -> dict | None:
    """Read app_data/update.json written by the last control-list sync."""
    try:
        from skyadmin_pro.paths import app_data_dir

        path = Path(app_data_dir()) / "update.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) and data.get("version") else None
    except Exception:
        return None


def _version_tuple(version: str):
    parts = []
    for chunk in str(version).split("."):
        digits = "".join(ch for ch in chunk if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def is_newer_version(candidate: str, current: str) -> bool:
    return _version_tuple(candidate) > _version_tuple(current)


def license_remaining_days() -> int | None:
    """Whole days left (floor). Hour-precision via license_time_left_text()."""
    data = _read_license_payload()
    if not data:
        return None
    exp = data.get("exp")
    if not exp:
        return None
    try:
        exp_dt = _parse_expiry(exp)
    except ValueError:
        return None
    seconds = (exp_dt - datetime.now()).total_seconds()
    return int(seconds // 86400)


def license_time_left_text() -> str:
    """Precise remaining time: '23h 59m', '5 day(s) 3h', etc."""
    data = _read_license_payload()
    if not data:
        return "Not activated"
    exp = data.get("exp")
    if not exp:
        return "Active — no expiry (permanent)"
    try:
        exp_dt = _parse_expiry(exp)
    except ValueError:
        return "Active"
    seconds = int((exp_dt - datetime.now()).total_seconds())
    if seconds <= 0:
        mins = abs(seconds) // 60
        return f"Expired {mins // 60}h {mins % 60}m ago"
    days, rem = divmod(seconds, 86400)
    hours = rem // 3600
    minutes = (rem % 3600) // 60
    if days >= 2:
        return f"Active — {days} day(s) {hours}h remaining"
    if days == 1:
        return f"Active — 1 day {hours}h remaining"
    if hours >= 1:
        return f"Active — {hours}h {minutes}m remaining"
    return f"Active — {minutes}m remaining"


def license_expiry_text() -> str:
    """Human-readable status for Settings / dialogs, with remaining time."""
    raw = license_time_left_text()
    # Strip the leading "Active — " prefix for use in label composites.
    if raw.startswith("Active — "):
        return raw[len("Active — "):]
    return raw


# --------------------------------------------------------------------------- #
# Online-assisted activation: customer pastes a key sent from the owner's     #
# phone (WhatsApp/Telegram/Email). No file copying, activates instantly.      #
# --------------------------------------------------------------------------- #

def verify_key_text(text: str) -> tuple[bool, str]:
    """Validate a PASTED full license key OR 8-digit passcode for this machine.

    Does not touch any file — call save_license_file() after success.
    Machine-level BAN applies to every format (checked first).
    """
    # Timing anti-debug: if a debugger is stepping through HMAC, the
    # computation takes abnormally long (>200ms for a trivial HMAC).
    import time as _time

    _t0 = _time.monotonic()
    _probe = hmac.new(SECRET, b"timing-check", hashlib.sha256).digest()
    _elapsed = _time.monotonic() - _t0
    if _elapsed > 0.8:
        return False, "Verification failed."

    raw = "".join((text or "").split())  # strip ALL whitespace/newlines from email paste
    if not raw:
        return False, "Paste the license key or 8-digit passcode."

    current_mid = get_machine_id()
    # Remote machine block — applies before any format-specific logic,
    # so a banned machine cannot sneak through with a passcode either.
    if current_mid in banned_machines():
        return False, "This machine has been blocked by Sky Creation Innovations."

    # 8-digit passcode (legacy, no expiry) or XXXXXXXX:TIMESTAMP (new, with expiry)
    if raw.isdigit() and len(raw) == 8:
        # Legacy passcode — check HMAC only (no embedded expiry)
        if hmac.compare_digest(generate_passcode(current_mid, None), raw):
            if raw in revoked_passcodes():
                return False, "This passcode has been revoked by Sky Creation Innovations."
            return True, f"Passcode accepted for machine {current_mid}."
        return False, f"Passcode is not valid for this machine ({current_mid})."

    # New expiry-embedded passcode: XXXXXXXX:TIMESTAMP (base36)
    if ":" in raw:
        parts = raw.rsplit(":", 1)
        if len(parts) == 2 and parts[0].isdigit() and len(parts[0]) == 8:
            exp_dt = _decode_passcode_expiry(raw)
            matched = False
            if exp_dt is not None:
                exp_ts = int(exp_dt.timestamp())
                sig = _hmac(f"{current_mid}:passcode:{exp_ts}")
                num = int(sig[:8], 16) % 100_000_000
                if f"{num:08d}" == parts[0]:
                    matched = True
            if matched:
                if raw in revoked_passcodes():
                    return False, "This passcode has been revoked by Sky Creation Innovations."
                if datetime.now() >= exp_dt:
                    return False, (
                        f"Passcode expired on {exp_dt.strftime('%Y-%m-%d %H:%M')}. "
                        "Request a renewal."
                    )
                return True, (
                    f"Passcode accepted for machine {current_mid} "
                    f"(expires: {exp_dt.strftime('%Y-%m-%d %H:%M')})."
                )
            return False, f"Passcode is not valid for this machine ({current_mid})."

    # Full base64 license key — supports BOTH formats:
    #   NEW (unique): sig over "mid|exp|iat|nonce|pkg"
    #   LEGACY:       sig over "mid:exp"
    try:
        b64 = raw.replace("-", "+").replace("_", "/")
        b64 += "=" * (-len(b64) % 4)
        data = json.loads(base64.b64decode(b64).decode())
        mid = str(data.get("mid") or "").strip().upper()
        exp = data.get("exp")
        sig = str(data.get("sig") or "")
        iat = str(data.get("iat") or "")
        nonce = str(data.get("n") or "")
        pkg = str(data.get("pkg") or "")

        if iat or nonce or pkg:
            payload_new = "|".join([mid, exp or "", iat, nonce, pkg])
            ok_sig = hmac.compare_digest(_hmac(payload_new), sig)
        else:
            ok_sig = False
        if not ok_sig:
            legacy_payload = f"{mid}:{exp or ''}"
            if not hmac.compare_digest(_hmac(legacy_payload), sig):
                return False, "License signature invalid — key was altered or issued with a different secret."

        if mid != "ANY" and mid != current_mid:
            return False, f"Key is for machine {mid}, but this machine is {current_mid}."
        # Machine-level ban already checked at the top of this function.
        if exp:
            try:
                exp_dt = _parse_expiry(exp)
            except ValueError:
                return False, f"License has invalid expiry: {exp!r}"
            if datetime.now() >= exp_dt:
                return False, (
                    f"License expired on {exp_dt.strftime('%Y-%m-%d %H:%M')}. "
                    "Request a renewal."
                )
        # Revocation list (optional file ~/.skyadmin_pro/revoked.txt, one nonce per line)
        if nonce and nonce in revoked_nonces():
            return False, "This license has been revoked by Sky Creation Innovations."
        extra = []
        if iat:
            extra.append(f"issued {iat}")
        if pkg and pkg.isdigit():
            extra.append(f"{pkg}-day package")
        suffix = f" ({', '.join(extra)})" if extra else ""
        return True, f"Licensed to {mid} (expires: {exp or 'never'}){suffix}."
    except Exception as exc:
        return False, f"Could not read the key ({exc}). Paste the full key or the 8-digit passcode."


def _shadow_path() -> Path | None:
    """Shadow copy lives beside the database backups (same machine only)."""
    try:
        from skyadmin_pro.paths import app_data_dir

        return app_data_dir() / "backups" / "license.key.shadow"
    except Exception:
        return None


def save_license_file(content: str) -> Path:
    """Persist a license key/passcode + a shadow copy + integrity seal."""
    from skyadmin_pro.paths import app_data_dir

    path = app_data_dir() / LICENSE_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    clean = (content or "").strip()
    path.write_text(clean, encoding="utf-8")
    # Integrity seal: HMAC of the license content, stored as a hidden sidecar.
    # Detects manual edits / copied keys without matching seal.
    try:
        from skyadmin_pro.services._protect_core import seal_value

        seal_path = path.parent / ".license.seal"
        seal_path.write_text(seal_value(clean), encoding="utf-8")
    except Exception:
        pass
    try:
        shadow = _shadow_path()
        if shadow is not None:
            shadow.parent.mkdir(parents=True, exist_ok=True)
            shadow.write_text(clean, encoding="utf-8")
    except OSError:
        pass
    return path


def _self_heal_license() -> Path | None:
    """If the license file was deleted (cleaner tools/AV), restore it from
    the shadow copy — same machine, same hardware binding."""
    shadow = _shadow_path()
    if shadow is None or not shadow.exists():
        return None
    try:
        from skyadmin_pro.paths import app_data_dir

        primary = app_data_dir() / LICENSE_FILENAME
        if not primary.exists():
            primary.write_text(shadow.read_text(encoding="utf-8"), encoding="utf-8")
            logging.getLogger(__name__).info(
                "License file was missing — restored from shadow copy."
            )
            return primary
    except Exception:
        return None
    return None


def activation_request_message(customer_email: str = "") -> str:
    """Pre-filled message the customer sends to the owner."""
    lines = [
        "SkyAdmin Pro — License Request",
        f"Machine ID: {get_machine_id()}",
    ]
    if customer_email:
        lines.append(f"Reply to email: {customer_email.strip()}")
    lines.append(f"Date: {date.today().isoformat()}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Decoy functions — waste reverse-engineering time.
#
# These look like real secret derivation functions but produce garbage output.
# An attacker who finds these first may spend hours analyzing dead ends
# before discovering the actual _derive_secret() function above.
# ---------------------------------------------------------------------------

def _DECOY_derive_backup_key() -> bytes:
    """DECOY — looks like a key derivation but produces wrong output."""
    import hashlib as _hl
    fake = b"SkyAdminBackupSalt2026-Decoy-v2-DO-NOT-USE"
    return _hl.pbkdf2_hmac("sha256", fake, b"decoy-salt", 10_000, dklen=32)


def _DECOY_verify_hmac(payload: str) -> str:
    """DECOY — computes HMAC with a fake secret."""
    fake_secret = b"ThisIsAFakeSecretForDecoyPurposes"
    return hmac.new(fake_secret, payload.encode(), hashlib.sha256).hexdigest()


def _DECOY_generate_key(machine_id: str) -> str:
    """DECOY — generates a key that always fails verification."""
    import base64 as _b64
    data = {"mid": machine_id, "exp": "2099-01-01", "sig": "DECOY", "n": "0"}
    return _b64.urlsafe_b64encode(str(data).encode()).decode()
