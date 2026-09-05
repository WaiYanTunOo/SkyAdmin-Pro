#!/usr/bin/env python3
"""End-to-end release publish helper (local or CI).

Runs release_check, writes release notes, optionally creates a GitHub Release
and publishes the Worker LATEST update line.

Ship path asset is the Windows installer (SkyAdminPro-Setup-<version>.exe).

Usage:
  python scripts/publish_release.py --version 0.3.2 --exe dist/SkyAdminPro-Setup-0.3.2.exe
  python scripts/publish_release.py --version 0.3.2 --exe dist/SkyAdminPro-Setup-0.3.2.exe --github
  python scripts/publish_release.py --version 0.3.2 --url https://github.com/org/repo/releases/download/v0.3.2/SkyAdminPro-Setup-0.3.2.exe
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _run(cmd: list[str], *, env: dict[str, str] | None = None) -> None:
    print(f"\n$ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=ROOT, env=env, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(cmd)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish a SkyAdmin Pro release")
    parser.add_argument("--version", required=True, help="Release version, e.g. 0.3.2")
    parser.add_argument(
        "--exe",
        type=Path,
        default=None,
        help="Path to ship artifact (default: dist/SkyAdminPro-Setup-<version>.exe)",
    )
    parser.add_argument("--notes", type=Path, default=ROOT / "dist" / "RELEASE_NOTES.md")
    parser.add_argument("--url", default="", help="Public download URL for publish_update.py")
    parser.add_argument("--api-url", default="", help="Worker base URL override")
    parser.add_argument("--token", default="", help="Worker API token (or SKYADMIN_API_TOKEN)")
    parser.add_argument("--skip-release-check", action="store_true")
    parser.add_argument("--require-signature", action="store_true")
    parser.add_argument("--skip-worker", action="store_true", help="Do not call publish_update.py")
    parser.add_argument("--github", action="store_true", help="Create GitHub release with gh CLI")
    parser.add_argument("--repo", default="", help="GitHub repo owner/name (default: origin remote)")
    args = parser.parse_args()

    version = args.version.lstrip("v").strip()
    exe = (args.exe or (ROOT / "dist" / f"SkyAdminPro-Setup-{version}.exe")).resolve()
    if not exe.is_file():
        print(f"ERROR: executable not found: {exe}", file=sys.stderr)
        return 1

    if not args.skip_release_check:
        check_cmd = [sys.executable, "scripts/release_check.py", "--skip-pytest", "--exe", str(exe)]
        if args.require_signature:
            check_cmd.append("--require-signature")
        _run(check_cmd)

    _run(
        [
            sys.executable,
            "scripts/generate_changelog.py",
            "--version",
            version,
            "--output",
            str(args.notes.resolve()),
        ]
    )

    download_url = (args.url or "").strip()
    if args.github:
        repo = (args.repo or "").strip()
        if not repo:
            repo = subprocess.check_output(
                ["git", "remote", "get-url", "origin"],
                cwd=ROOT,
                text=True,
            ).strip()
            if repo.endswith(".git"):
                repo = repo[:-4]
            if "github.com" in repo:
                repo = repo.split("github.com/", 1)[-1]
        tag = f"v{version}"
        asset_name = exe.name
        _run(
            [
                "gh",
                "release",
                "create",
                tag,
                str(exe),
                "--title",
                f"SkyAdmin Pro {version}",
                "--notes-file",
                str(args.notes.resolve()),
            ],
            env={**os.environ, "GH_REPO": repo} if repo else None,
        )
        download_url = f"https://github.com/{repo}/releases/download/{tag}/{asset_name}"

    if not args.skip_worker:
        if not download_url:
            print("WARN: no --url and --github not used; skipping Worker publish.", file=sys.stderr)
        else:
            token = (args.token or os.environ.get("SKYADMIN_API_TOKEN") or "").strip()
            if not token:
                print("WARN: SKYADMIN_API_TOKEN not set; skipping Worker publish.", file=sys.stderr)
            else:
                cmd = [
                    sys.executable,
                    "scripts/publish_update.py",
                    "--version",
                    version,
                    "--url",
                    download_url,
                ]
                api_url = (args.api_url or os.environ.get("SKYADMIN_API_URL") or "").strip()
                if api_url:
                    cmd.extend(["--api-url", api_url])
                cmd.extend(["--token", token])
                _run(cmd)

    print(f"\nRelease {version} publish flow complete.")
    if download_url:
        print(f"Download URL: {download_url}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
