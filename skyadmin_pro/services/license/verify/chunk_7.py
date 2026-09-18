from __future__ import annotations

import base64
import json
from datetime import datetime

from skyadmin_pro.services.license_crypto import (
    verify_license_signature,
)
from skyadmin_pro.services.license_public import (
    LEGACY_FORMAT_SUNSET_MESSAGE,
    LICENSE_SIGNATURE_ALGORITHM,
)

from .chunk_2 import _parse_expiry, _read_license_payload


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
    except (OSError, ValueError):
        return frozenset()


def _verify_parsed_license(raw: str, current_mid: str) -> tuple[bool, str]:
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
        algorithm = str(data.get("alg") or "")

        if algorithm != LICENSE_SIGNATURE_ALGORITHM:
            return False, LEGACY_FORMAT_SUNSET_MESSAGE

        if not verify_license_signature(
            mid=mid,
            exp=str(exp) if exp is not None else None,
            iat=iat,
            nonce=nonce,
            pkg=pkg,
            signature=sig,
            algorithm=algorithm,
        ):
            return (
                False,
                "License signature invalid — key was altered, issued with a different signing key, or the Worker LICENSE_ED25519_PRIVATE_KEY_B64 does not match this app build.",
            )

        if mid != "ANY" and mid != current_mid:
            return False, f"Key is for machine {mid}, but this machine is {current_mid}."
        if exp:
            try:
                exp_dt = _parse_expiry(exp)
            except ValueError:
                return False, f"License has invalid expiry: {exp!r}"
            saved_payload = _read_license_payload()
            saved_nonce = str((saved_payload or {}).get("n") or "")
            is_saved_here = bool(nonce and nonce == saved_nonce)
            if datetime.now() >= exp_dt:
                if not is_saved_here and pkg and str(pkg).isdigit():
                    return (
                        False,
                        f"Activation window expired on {exp_dt.strftime('%Y-%m-%d %H:%M')} (must activate within 24 hours). Request a new license.",
                    )
                return False, f"License expired on {exp_dt.strftime('%Y-%m-%d %H:%M')}. Request a renewal."
        if nonce and nonce in revoked_nonces():
            return False, "This license has been revoked by Sky Creation Innovations."
        extra = []
        if iat:
            extra.append(f"issued {iat}")
        if pkg and pkg.isdigit():
            extra.append(f"{pkg}-day package")
        suffix = f" ({', '.join(extra)})" if extra else ""
        return True, f"Licensed to {mid} (expires: {exp or 'never'}){suffix}."
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        return False, f"Could not read the key ({exc}). Paste a current license key or SKYPASS1 passcode."
    return False, "Verification failed."
