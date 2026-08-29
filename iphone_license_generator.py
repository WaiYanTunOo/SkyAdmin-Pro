#!/usr/bin/env python3
"""iPhone License Generator — Sky Creation Innovations
Run on your iPhone in Pythonista, a-Shell, or any Python 3 app.
Supports online (Cloudflare API) and offline (local SECRET) modes.

Usage:
  python iphone_license_generator.py
  # then enter Machine ID shown on the PC
  # or: python iphone_license_generator.py 72FA00DC6B64525F 365

API mode (preferred — no SECRET on this device):
  export SKYADMIN_API_URL=https://your-api.workers.dev
  export SKYADMIN_API_TOKEN=your-owner-token
  python iphone_license_generator.py 72FA00DC6B64525F 365

Offline mode (SECRET stays on device):
  python iphone_license_generator.py 72FA00DC6B64525F 365
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets as _secrets
import sys
from datetime import date, datetime, timedelta
from typing import Optional

# ── XOR-interleaved SECRET (offline fallback only) ──────────────────────────
# Same derivation as skyadmin_pro/services/license.py.
_XK = [0x5B, 0x2E]
_XF = [
    ([8, 48, 34, 24], [41, 62, 58, 47]),
    ([71, 65, 64, 103], [64, 64, 65, 88]),
    ([58, 47, 50, 52], [53, 40, 118, 105]),
    ([30, 28, 24, 3], [125, 69, 87, 111]),
    ([63, 54, 50, 53], [11, 41, 52, 120]),
    ([126, 92, 65, 94], [92, 71, 75, 90]),
    ([58, 41], [34, 122]),
]


def _derive_secret() -> bytes:
    parts_a, parts_b = [], []
    for idx, (ea, eb) in enumerate(_XF):
        k = _XK[idx % len(_XK)]
        parts_a.append(bytes(c ^ k for c in ea))
        parts_b.append(bytes(c ^ k for c in eb))
    return b"".join(a + b for a, b in zip(parts_a, parts_b))


SECRET = _derive_secret()


def _hmac(payload: str) -> str:
    return hmac.new(SECRET, payload.encode(), hashlib.sha256).hexdigest()


# ── API helper ───────────────────────────────────────────────────────────────

def _api_call(method: str, path: str, body: dict | None = None,
              api_url: str = "", api_token: str = "") -> dict:
    """Call the Cloudflare Worker API. Raises on error."""
    import urllib.request
    import urllib.error

    url = api_url.rstrip("/") + path
    headers = {"Content-Type": "application/json"}
    if api_token:
        headers["Authorization"] = f"Bearer {api_token}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read())
    if not result.get("ok"):
        raise RuntimeError(result.get("error", "API error"))
    return result


# ── Offline generation (local SECRET) ───────────────────────────────────────

def generate_license_offline(machine_id: str, days_valid: int | None = 365) -> tuple[str, str, str]:
    """Offline generation. Returns (license_key, issued_at, nonce)."""
    mid = machine_id.strip().upper()
    now = datetime.now()
    exp = None
    if days_valid is not None:
        exp = (now + timedelta(days=days_valid)).replace(microsecond=0).isoformat(timespec="seconds")
    iat = now.strftime("%Y-%m-%dT%H:%M")
    nonce = _secrets.token_hex(6)
    pkg = str(days_valid) if days_valid is not None else ""
    payload = "|".join([mid, exp or "", iat, nonce, pkg])
    sig = _hmac(payload)
    data = {"mid": mid, "exp": exp, "sig": sig, "iat": iat, "n": nonce, "pkg": pkg}
    raw = json.dumps(data, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("="), iat, nonce


def generate_passcode_offline(machine_id: str, days_valid: int | None = None) -> str:
    """Offline passcode: 8-digit legacy or XXXXXXXX:b36(expiry_ts)."""
    import string as _str

    mid = machine_id.strip().upper()
    if days_valid is not None:
        exp_dt = (datetime.now() + timedelta(days=days_valid)).replace(microsecond=0)
        exp_ts = int(exp_dt.timestamp())
        sig = _hmac(f"{mid}:passcode:{exp_ts}")
        num = int(sig[:8], 16) % 100_000_000
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


# ── Online generation (API) ─────────────────────────────────────────────────

def generate_license_online(machine_id: str, days: int | None, price: int,
                            api_url: str, api_token: str) -> dict:
    """Call POST /api/generate. Returns dict with license_key, passcode, nonce, etc."""
    return _api_call("POST", "/api/generate", {
        "mid": machine_id.strip().upper(),
        "days": days,
        "price": price,
    }, api_url, api_token)


# ── CSV logging ──────────────────────────────────────────────────────────────

def log_license(csv_path: str, machine_id: str, days_valid, exp, iat, nonce,
                passcode: str, key: str) -> None:
    """Append issuance to issued_licenses.csv."""
    import csv
    import os

    new_file = not os.path.exists(csv_path)
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["issued", "machine_id", "package_days", "expires",
                        "nonce", "passcode", "license_key", "status"])
        w.writerow([iat, machine_id, days_valid if days_valid is not None else "unlimited",
                    exp or "never", nonce, passcode, key, "ACTIVE"])


# ── Main ─────────────────────────────────────────────────────────────────────

PRICE_MAP = {1: 50, 7: 500, 30: 800, 365: 9000}


def main() -> None:
    api_url = os.environ.get("SKYADMIN_API_URL", "").strip()
    api_token = os.environ.get("SKYADMIN_API_TOKEN", "").strip()
    offline_mode = not api_url

    if len(sys.argv) >= 2:
        mid = sys.argv[1]
        arg = sys.argv[2] if len(sys.argv) >= 3 else ""
        if arg.lower() == "never":
            days = None
        elif arg.lstrip("-").isdigit() and int(arg) > 0:
            days = int(arg)
        else:
            days = 365
    else:
        print("SkyAdmin Pro — License Generator")
        print("Sky Creation Innovations\n")
        if offline_mode:
            print("[OFFLINE MODE — using local SECRET]\n")
        else:
            print(f"[ONLINE MODE — API: {api_url}]\n")
        print("Prices: 1 Day=50 Baht | 7 Days=500 Baht | 30 Days=800 Baht | 1 Year=9,000 Baht\n")
        mid = input("Enter Machine ID from PC (16 hex, e.g. 72FA00DC6B64525F): ").strip()
        print("\nPackage: [1] 1 Day  [7] 7 Days  [30] 30 Days  [365] 1 Year")
        raw_days = input("Enter days (or a custom number, or 'never'): ").strip()
        if raw_days.lower() == "never":
            days = None
        elif raw_days == "":
            days = 7
        else:
            try:
                days = int(raw_days)
            except ValueError:
                days = 7

    mid = mid.strip().upper()
    if not mid or len(mid) != 16 or any(c not in "0123456789ABCDEF" for c in mid):
        print("Error: Machine ID must be 16 hex characters.")
        sys.exit(1)

    price = PRICE_MAP.get(days)
    mode = "ONLINE" if not offline_mode else "OFFLINE"

    if not offline_mode:
        try:
            result = generate_license_online(mid, days, price or 0, api_url, api_token)
            lic = result["license_key"]
            code = result["passcode"]
            iat = result["issued_at"]
            nonce = result["nonce"]
            exp_str = result.get("expires_at", "never")
        except Exception as e:
            print(f"\nAPI call failed ({e}), falling back to offline mode...\n")
            offline_mode = True

    if offline_mode:
        lic, iat, nonce = generate_license_offline(mid, days)
        code = generate_passcode_offline(mid, days)
        exp_dt = None if days is None else datetime.now() + timedelta(days=days)
        exp_str = exp_dt.strftime("%Y-%m-%d %H:%M") if exp_dt else "never"

    print("\n" + "=" * 60)
    print(f"Mode       : {mode}")
    print(f"Machine ID : {mid}")
    print(f"Package    : {'Unlimited' if days is None else f'{days} days'}"
          + (f"  ({price:,} Baht)" if price else ""))
    print(f"Issued     : {iat}")
    print(f"Expires    : {exp_str}")
    print("=" * 60)
    print("\nLICENSE KEY:\n")
    print(lic)
    print("\nPASSCODE:\n")
    print(code)
    print("\n" + "=" * 60)

    try:
        log_license("issued_licenses.csv", mid, days, exp_str, iat, nonce, code, lic)
        print("Recorded -> issued_licenses.csv")
    except OSError as exc:
        print(f"(Could not write CSV record: {exc})")

    print("\nOne-time-use enforcement:")
    print("• The app burns this code locally on first activation.")
    if not offline_mode:
        print("• It is also recorded server-side (API) and cannot be reused.")
    else:
        print(f"• USED {nonce}")
    print("=" * 60)


if __name__ == "__main__":
    main()
