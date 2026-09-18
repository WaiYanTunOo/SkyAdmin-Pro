from __future__ import annotations

from .chunk_3 import license_time_left_text
from .chunk_8 import verify_key_text


def _verify_integrity() -> bool:
    """Verify that critical license functions haven't been patched."""
    try:
        import inspect as _inspect

        src = _inspect.getsource(verify_key_text)
        if "banned_machines" not in src:
            return False
        if "revoked_nonces" not in src:
            return False
        return "verify_license_signature" in src
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


def license_expiry_text() -> str:
    """Human-readable status for Settings / dialogs, with remaining time."""
    raw = license_time_left_text()
    # Strip the leading "Active — " prefix for use in label composites.
    if raw.startswith("Active — "):
        return raw[len("Active — ") :]
    return raw


def generate_passcode(*_args: object, **_kwargs: object) -> str:
    """Disabled in the desktop client — passcodes are issued by the Worker API."""
    raise RuntimeError(
        "Passcode generation is server-side only. "
        "Use POST /api/generate on the SkyAdmin Worker (owner tools), not the desktop app."
    )
