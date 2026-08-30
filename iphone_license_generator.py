#!/usr/bin/env python3
"""iPhone License Generator — Sky Creation Innovations.

Issues licenses via the Cloudflare Worker API only (no offline signing secret).

Usage:
  export SKYADMIN_API_URL=https://skyadmin-worker.skyadmin-pro.workers.dev
  export SKYADMIN_API_TOKEN=your-owner-token
  python iphone_license_generator.py 72FA00DC6B64525F 365
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime

DEFAULT_API_URL = "https://skyadmin-worker.skyadmin-pro.workers.dev"
FALLBACK_PRICE_MAP = {1: 50, 7: 500, 30: 800, 365: 9000}


def _api_call(method: str, path: str, body: dict | None, api_url: str, api_token: str) -> dict:
    import urllib.request

    url = api_url.rstrip("/") + path
    headers = {"Content-Type": "application/json", "User-Agent": "SkyAdminPro"}
    if api_token:
        headers["Authorization"] = f"Bearer {api_token}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read())
    if not result.get("ok"):
        raise RuntimeError(result.get("error", "API error"))
    return result


def fetch_pricing_map(api_url: str) -> dict[int, int]:
    try:
        data = _api_call("GET", "/api/pricing", None, api_url, "")
        prices: dict[int, int] = {}
        for item in data.get("packages") or []:
            if not isinstance(item, dict):
                continue
            days = item.get("days")
            if days is None:
                continue
            prices[int(days)] = int(item.get("price_thb") or item.get("price") or 0)
        return prices or dict(FALLBACK_PRICE_MAP)
    except Exception:
        return dict(FALLBACK_PRICE_MAP)


def check_signing_key_alignment(api_url: str) -> None:
    from skyadmin_pro.services.license_public import ED25519_PUBLIC_KEY_HEX

    try:
        data = _api_call("GET", "/api/signing/public-key", None, api_url, "")
    except Exception:
        return
    worker_hex = str(data.get("public_key_hex") or "").lower()
    if worker_hex and worker_hex != ED25519_PUBLIC_KEY_HEX.lower():
        print(
            "WARNING: Worker signing key does NOT match this desktop build.\n"
            "Codes from the admin site will fail activation until LICENSE_ED25519_PRIVATE_KEY_B64\n"
            f"matches license_public.py (client key starts with {ED25519_PUBLIC_KEY_HEX[:8]}…).\n",
            file=sys.stderr,
        )


def generate_license_online(machine_id: str, days: int | None, price: int, api_url: str, api_token: str) -> dict:
    return _api_call(
        "POST",
        "/api/generate",
        {"mid": machine_id.strip().upper(), "days": days, "price": price},
        api_url,
        api_token,
    )


def log_license(csv_path: str, machine_id: str, days_valid, exp, iat, nonce, passcode: str, key: str) -> None:
    new_file = not os.path.exists(csv_path)
    with open(csv_path, "a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        if new_file:
            writer.writerow(
                ["issued", "machine_id", "package_days", "expires", "nonce", "passcode", "license_key", "status"]
            )
        writer.writerow(
            [
                iat,
                machine_id,
                days_valid if days_valid is not None else "unlimited",
                exp or "never",
                nonce,
                passcode,
                key,
                "ACTIVE",
            ]
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="SkyAdmin Pro license generator (Worker API)")
    parser.add_argument("machine_id", nargs="?", help="16-hex machine ID")
    parser.add_argument("days", nargs="?", help="Package days or 'never'")
    parser.add_argument("--api-url", default=os.environ.get("SKYADMIN_API_URL", DEFAULT_API_URL).strip())
    parser.add_argument("--api-token", default=os.environ.get("SKYADMIN_API_TOKEN", "").strip())
    args = parser.parse_args()

    api_url = (args.api_url or DEFAULT_API_URL).strip()
    api_token = (args.api_token or "").strip()
    if not api_url or not api_token:
        print(
            "Error: set SKYADMIN_API_URL and SKYADMIN_API_TOKEN (or pass --api-url / --api-token).\n"
            "Offline signing was removed — licenses must be issued by the Worker API.",
            file=sys.stderr,
        )
        sys.exit(1)

    check_signing_key_alignment(api_url)
    price_map = fetch_pricing_map(api_url)

    if args.machine_id:
        mid = args.machine_id
        arg = args.days or ""
        if arg.lower() == "never":
            days = None
        elif arg.lstrip("-").isdigit() and int(arg) > 0:
            days = int(arg)
        else:
            days = 365
    else:
        print("SkyAdmin Pro — License Generator")
        print("Sky Creation Innovations\n")
        print(f"[ONLINE MODE — API: {api_url}]\n")
        tiers = ", ".join(f"{d}d={p:,}฿" for d, p in sorted(price_map.items()))
        print(f"Prices: {tiers}\n")
        mid = input("Enter Machine ID from PC (16 hex, e.g. 72FA00DC6B64525F): ").strip()
        print("\nPackage: enter days (1, 7, 30, 365) or a custom number, or 'never'")
        raw_days = input("Days: ").strip()
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

    price = price_map.get(days, 0) if days is not None else 0
    try:
        result = generate_license_online(mid, days, price, api_url, api_token)
    except Exception as exc:
        print(f"\nAPI call failed: {exc}", file=sys.stderr)
        sys.exit(1)

    lic = result["license_key"]
    code = result["passcode"]
    iat = result["issued_at"]
    nonce = result["nonce"]
    exp_str = result.get("expires_at") or "never"

    print("\n" + "=" * 60)
    print("Mode       : ONLINE")
    print(f"Machine ID : {mid}")
    print(f"Package    : {'Unlimited' if days is None else f'{days} days'}" + (f"  ({price:,} Baht)" if price else ""))
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
    print("• It is also recorded server-side (API) and cannot be reused.")
    print("=" * 60)


if __name__ == "__main__":
    main()
