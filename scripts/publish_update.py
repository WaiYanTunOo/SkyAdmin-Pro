#!/usr/bin/env python3
"""Publish a desktop app update on the Worker (LATEST line on control list).

Ship path URL is the Windows installer (SkyAdminPro-Setup-<version>.exe), not the portable exe.

Usage:
  python scripts/publish_update.py --version 0.3.2 --url https://cdn.example/SkyAdminPro-Setup-0.3.2.exe
  python scripts/publish_update.py --version 0.3.2 --url https://cdn.example/SkyAdminPro-Setup-0.3.2.exe --api-url https://worker.example --token YOUR_API_TOKEN
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish SkyAdmin Pro app update on Worker")
    parser.add_argument("--version", required=True, help="Semantic version, e.g. 0.3.2")
    parser.add_argument("--url", default="", help="Public download URL for the new build")
    parser.add_argument("--api-url", default="", help="Worker base URL (default: config.API_BASE_URL)")
    parser.add_argument("--token", default="", help="Worker API_TOKEN (or set SKYADMIN_API_TOKEN)")
    args = parser.parse_args()

    api_url = (args.api_url or "").strip()
    if not api_url:
        try:
            from skyadmin_pro.config import API_BASE_URL

            api_url = (API_BASE_URL or "").strip()
        except Exception:
            api_url = ""
    if not api_url:
        print("ERROR: set --api-url or configure API_BASE_URL in skyadmin_pro/config.py", file=sys.stderr)
        return 1

    token = (args.token or os.environ.get("SKYADMIN_API_TOKEN") or "").strip()
    if not token:
        print("ERROR: pass --token or set SKYADMIN_API_TOKEN", file=sys.stderr)
        return 1

    body = json.dumps({"version": args.version.strip(), "url": (args.url or "").strip()}).encode()
    req = urllib.request.Request(
        api_url.rstrip("/") + "/api/update",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "SkyAdminPro",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read(4096))
    except urllib.error.HTTPError as exc:
        detail = exc.read(4096).decode("utf-8", errors="replace")
        print(f"ERROR: HTTP {exc.code}: {detail}", file=sys.stderr)
        return 1
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"ERROR: request failed: {exc}", file=sys.stderr)
        return 1

    if not payload.get("ok"):
        print(f"ERROR: {payload.get('error', payload)}", file=sys.stderr)
        return 1

    print(payload.get("message") or f"Published v{args.version}")
    if args.url:
        print(f"Download: {args.url}")
    print("Desktop apps will see this after Sync Now or the next daily control-list fetch.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
