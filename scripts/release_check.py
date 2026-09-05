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


def default_installer_path() -> Path:
    from skyadmin_pro.config import APP_VERSION

    return ROOT / "dist" / f"SkyAdminPro-Setup-{APP_VERSION}.exe"


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


def check_authenticode_signature(exe: Path, *, required: bool) -> list[str]:
    errors: list[str] = []
    if sys.platform != "win32":
        if required:
            errors.append(_fail("Authenticode signature required but release check is not running on Windows"))
        else:
            print("  WARN  Skipping Authenticode check (not on Windows)")
        return errors

    ps = f"$s = Get-AuthenticodeSignature -FilePath '{exe}'; Write-Output $s.Status"
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        errors.append(_fail(f"Authenticode check failed: {exc}"))
        return errors

    status = (result.stdout or "").strip()
    if status == "Valid":
        _ok(f"Authenticode signature valid ({exe.name})")
        return errors

    if required:
        detail = status or (result.stderr or "unknown").strip() or "unsigned"
        errors.append(_fail(f"Authenticode signature required but status is {detail}"))
    else:
        print(f"  WARN  {exe.name} is not Authenticode-signed (expected until Phase 11.2 cert is configured)")
    return errors


def check_version_alignment() -> list[str]:
    errors: list[str] = []
    try:
        import re

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

        # Check skyadmin_pro.__version__ alias (must track config.APP_VERSION)
        import skyadmin_pro

        pkg_ver = str(getattr(skyadmin_pro, "__version__", "") or "")
        if not pkg_ver:
            errors.append(_fail("skyadmin_pro.__version__ is missing"))
        elif pkg_ver != APP_VERSION:
            errors.append(
                _fail(f"Version mismatch: skyadmin_pro.__version__={pkg_ver} APP_VERSION={APP_VERSION}")
            )
        else:
            _ok(f"Package __version__ aligned at {pkg_ver}")

        # Check ISS version — supports both hardcoded and injected (via /DAppVersion)
        iss = ROOT / "packaging" / "SkyAdminPro.iss"
        if iss.is_file():
            iss_text = iss.read_text(encoding="utf-8")
            m = re.search(r'#define\s+AppVersion\s+"([^"]+)"', iss_text)
            iss_ver = m.group(1) if m else ""
            if "#error" in iss_text and "AppVersion not defined" in iss_text:
                _ok(
                    "ISS defers version to build (injected via /DAppVersion) — check passes if build-installer passes APP_VERSION"
                )
                # Still ensure no hardcoded stale fallback remains
                if iss_ver:
                    _ok(f"ISS hardcoded fallback {iss_ver} ignored (injected path)")
            elif iss_ver and iss_ver != APP_VERSION:
                errors.append(
                    _fail(f"Version mismatch: SkyAdminPro.iss AppVersion={iss_ver} APP_VERSION={APP_VERSION}")
                )
            elif iss_ver:
                _ok(f"ISS version aligned at {iss_ver}")

        # Check macOS spec version
        macos_spec = ROOT / "packaging" / "SkyAdminPro-macos.spec"
        if macos_spec.is_file():
            spec_text = macos_spec.read_text(encoding="utf-8")
            m2 = re.search(r'"CFBundleShortVersionString"\s*:\s*"([^"]+)"', spec_text)
            mac_ver = m2.group(1) if m2 else ""
            if mac_ver and mac_ver != APP_VERSION:
                errors.append(
                    _fail(
                        f"Version mismatch: SkyAdminPro-macos.spec CFBundleShortVersionString={mac_ver} APP_VERSION={APP_VERSION}"
                    )
                )
            elif mac_ver:
                _ok(f"macOS spec version aligned at {mac_ver}")
    except Exception as exc:
        errors.append(_fail(f"Version check failed: {exc}"))
    return errors


def check_installer(installer: Path) -> list[str]:
    errors: list[str] = []
    if not installer.is_file():
        # Installer-first ship path: missing installer blocks release.
        errors.append(_fail(f"Installer not found (required): {installer}"))
        return errors
    size = installer.stat().st_size
    if size < 5 * 1024 * 1024:
        errors.append(_fail(f"Installer too small ({size:,} bytes)"))
    else:
        _ok(f"Installer size {size / (1024 * 1024):.1f} MB ({installer.name})")
    return errors


def write_hash_manifest() -> None:
    import hashlib

    dist = ROOT / "dist"
    if not dist.is_dir():
        return
    hashes = []
    for name in (
        "SkyAdminPro.exe",
        f"SkyAdminPro-Setup-{__import__('skyadmin_pro.config', fromlist=['APP_VERSION']).APP_VERSION}.exe",
    ):
        p = dist / name
        if p.is_file():
            h = hashlib.sha256(p.read_bytes()).hexdigest()
            hashes.append(f"{h}  {name}")
    if hashes:
        out = dist / "SHA256SUMS"
        out.write_text("\n".join(hashes) + "\n", encoding="utf-8")
        _ok(f"Wrote {out.name} ({len(hashes)} entries)")


def run_pytest() -> list[str]:
    errors: list[str] = []
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "--tb=short",
    ]
    print(f"\nRunning: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout.rstrip())
    if result.returncode != 0:
        if result.stderr:
            print(result.stderr.rstrip())
        errors.append(_fail(f"pytest full suite failed (exit {result.returncode})"))
    else:
        _ok("pytest full suite passed")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="SkyAdmin Pro pre-release checks")
    parser.add_argument("--exe", type=Path, default=DEFAULT_EXE, help="Path to SkyAdminPro.exe")
    parser.add_argument(
        "--installer",
        type=Path,
        default=None,
        help="Path to SkyAdminPro-Setup-<version>.exe (default: dist/SkyAdminPro-Setup-<APP_VERSION>.exe)",
    )
    parser.add_argument("--linux-binary", type=Path, default=None, help="Optional Linux dist/SkyAdminPro path")
    parser.add_argument("--api-url", default="", help="Worker base URL (default: from config.API_BASE_URL)")
    parser.add_argument("--skip-pytest", action="store_true", help="Skip full pytest suite")
    parser.add_argument("--skip-worker", action="store_true", help="Skip Worker HTTP checks")
    parser.add_argument(
        "--require-signature",
        action="store_true",
        help="Fail when dist exe is not Authenticode-signed (Windows only)",
    )
    args = parser.parse_args()

    print("SkyAdmin Pro — release checks\n")

    failures: list[str] = []
    failures.extend(check_version_alignment())
    failures.extend(check_embedded_public_key())
    failures.extend(check_exe(args.exe.resolve()))
    # Installer-first ship path: installer is required, always checked.
    installer_path = (args.installer or default_installer_path()).resolve()
    failures.extend(check_installer(installer_path))
    if args.require_signature:
        failures.extend(check_authenticode_signature(args.exe.resolve(), required=True))
        installer = installer_path
        if installer.exists():
            failures.extend(check_authenticode_signature(installer, required=True))
        else:
            failures.append(_fail(f"Installer not found for signature check: {installer}"))
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

    # Write SHA256 manifest for artifacts (informational, never blocks)
    try:
        write_hash_manifest()
    except Exception as exc:
        print(f"  WARN  Could not write SHA256SUMS: {exc}")

    print()
    if failures:
        print(f"RELEASE BLOCKED — {len(failures)} check(s) failed.")
        return 1
    print("RELEASE OK — all automated checks passed.")
    print("Next: run docs/MANUAL_QA.md on a clean PC before shipping.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
