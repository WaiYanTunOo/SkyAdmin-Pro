#!/usr/bin/env python3
"""Pre-release gate for SkyAdmin Pro — run before shipping dist/SkyAdminPro.exe.

Usage:
  python scripts/release_check.py
  python scripts/release_check.py --skip-pytest
  python scripts/release_check.py --exe path/to/SkyAdminPro.exe
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_EXE = ROOT / "dist" / "SkyAdminPro.exe"
MIN_EXE_BYTES = 10 * 1024 * 1024
FORBIDDEN_EXE_STRINGS = (
    b"skyadmin_pro.services.license_authoring",
    b"generate_ed25519_license",
)


def _ok(msg: str) -> None:
    print(f"  OK  {msg}")


def _fail(msg: str) -> str:
    print(f"  FAIL  {msg}")
    return msg


def check_exe(exe: Path) -> list[str]:
    errors: list[str] = []
    if not exe.is_file():
        errors.append(_fail(f"Executable not found: {exe}"))
        return errors
    size = exe.stat().st_size
    if size < MIN_EXE_BYTES:
        errors.append(_fail(f"Executable too small ({size:,} bytes) — expected a full PyInstaller build"))
    else:
        _ok(f"Executable size {size / (1024 * 1024):.1f} MB")

    data = exe.read_bytes()
    forbidden = False
    for needle in FORBIDDEN_EXE_STRINGS:
        if needle in data:
            errors.append(_fail(f"Forbidden string in binary: {needle.decode('utf-8', errors='replace')}"))
            forbidden = True
    if not forbidden:
        _ok("license_authoring not embedded in exe")

    return errors


def check_linux_binary(binary: Path) -> list[str]:
    """Optional check when packaging on Linux (dist/SkyAdminPro)."""
    return check_exe(binary)


def check_worker_api(api_url: str) -> list[str]:
    errors: list[str] = []
    base = api_url.rstrip("/")

    try:
        req = urllib.request.Request(base + "/api/ping", headers={"User-Agent": "SkyAdminPro"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            payload = json.loads(resp.read(4096))
        if not payload.get("ok"):
            errors.append(_fail("Worker /api/ping returned ok=false"))
        else:
            _ok(f"Worker ping ({payload.get('service', 'api')})")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        errors.append(_fail(f"Worker ping failed: {exc}"))
        return errors

    try:
        req = urllib.request.Request(
            base + "/api/signing/public-key",
            headers={"User-Agent": "SkyAdminPro"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            payload = json.loads(resp.read(8192))
        if not payload.get("ok"):
            errors.append(_fail(f"Signing info: {payload.get('error', 'unknown')}"))
        elif not payload.get("matches_desktop"):
            errors.append(_fail("Worker signing key does not match desktop build"))
        else:
            _ok("Worker signing key matches desktop")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        errors.append(_fail(f"Signing check failed: {exc}"))

    try:
        req = urllib.request.Request(base + "/api/pricing", headers={"User-Agent": "SkyAdminPro"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            payload = json.loads(resp.read(16384))
        packages = payload.get("packages") or []
        if not payload.get("ok") or not packages:
            errors.append(_fail("Worker /api/pricing missing packages"))
        else:
            _ok(f"Pricing API ({len(packages)} packages)")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        errors.append(_fail(f"Pricing check failed: {exc}"))

    try:
        req = urllib.request.Request(base + "/api/update", headers={"User-Agent": "SkyAdminPro"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            payload = json.loads(resp.read(4096))
        if not payload.get("ok"):
            errors.append(_fail("Worker /api/update returned ok=false"))
        else:
            ver = payload.get("version")
            _ok(f"Update API (published: {ver or 'none'})")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        errors.append(_fail(f"Update check failed: {exc}"))

    return errors


def check_embedded_public_key() -> list[str]:
    errors: list[str] = []
    pub_path = ROOT / "skyadmin_pro" / "services" / "license_public.py"
    text = pub_path.read_text(encoding="utf-8")
    if "b9bc4ee341f806f7cdfe698c048fc4b212e8b5ef6ebffcb63bc4d527d136b501" not in text:
        errors.append(_fail("license_public.py missing expected ED25519 public key"))
    else:
        _ok("Embedded public key present in license_public.py")
    return errors


def check_version_alignment() -> list[str]:
    errors: list[str] = []
    try:
        import tomllib

        from skyadmin_pro.config import APP_VERSION

        pyproject = ROOT / "pyproject.toml"
        if not pyproject.is_file():
            return errors
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        py_ver = str(data.get("project", {}).get("version") or "")
        if py_ver and py_ver != APP_VERSION:
            errors.append(_fail(f"Version mismatch: pyproject.toml={py_ver} config.APP_VERSION={APP_VERSION}"))
        else:
            _ok(f"Version aligned at {APP_VERSION}")
    except Exception as exc:
        errors.append(_fail(f"Version check failed: {exc}"))
    return errors


    errors: list[str] = []
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-m",
        "release or walkthrough",
        "--tb=short",
    ]
    print(f"\nRunning: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout.rstrip())
    if result.returncode != 0:
        if result.stderr:
            print(result.stderr.rstrip())
        errors.append(_fail(f"pytest release/walkthrough suite failed (exit {result.returncode})"))
    else:
        _ok("pytest release + walkthrough markers passed")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="SkyAdmin Pro pre-release checks")
    parser.add_argument("--exe", type=Path, default=DEFAULT_EXE, help="Path to SkyAdminPro.exe")
    parser.add_argument("--linux-binary", type=Path, default=None, help="Optional Linux dist/SkyAdminPro path")
    parser.add_argument("--api-url", default="", help="Worker base URL (default: from config.API_BASE_URL)")
    parser.add_argument("--skip-pytest", action="store_true", help="Skip pytest release/walkthrough suite")
    parser.add_argument("--skip-worker", action="store_true", help="Skip Worker HTTP checks")
    args = parser.parse_args()

    print("SkyAdmin Pro — release checks\n")

    failures: list[str] = []
    failures.extend(check_version_alignment())
    failures.extend(check_embedded_public_key())
    failures.extend(check_exe(args.exe.resolve()))
    if args.linux_binary:
        failures.extend(check_linux_binary(args.linux_binary.resolve()))

    api_url = (args.api_url or "").strip()
    if not api_url:
        try:
            from skyadmin_pro.config import API_BASE_URL

            api_url = (API_BASE_URL or "").strip()
        except Exception:
            api_url = ""

    if args.skip_worker:
        print("\n(Skipping Worker API checks)")
    elif api_url:
        print(f"\nWorker: {api_url}")
        failures.extend(check_worker_api(api_url))
    else:
        print("\n  WARN  API_BASE_URL not configured — skipping Worker checks")

    if not args.skip_pytest:
        failures.extend(run_pytest())

    print()
    if failures:
        print(f"RELEASE BLOCKED — {len(failures)} check(s) failed.")
        return 1
    print("RELEASE OK — all automated checks passed.")
    print("Next: run docs/MANUAL_QA.md on a clean PC before shipping.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
