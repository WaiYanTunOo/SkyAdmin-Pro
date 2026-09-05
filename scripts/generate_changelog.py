#!/usr/bin/env python3
"""Generate CHANGELOG.md sections from git tags and commit messages.

Usage:
  python scripts/generate_changelog.py
  python scripts/generate_changelog.py --write
  python scripts/generate_changelog.py --version 0.3.2 --write
  python scripts/generate_changelog.py --version 0.3.2 --output dist/RELEASE_NOTES.md
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parents[1]
CHANGELOG = ROOT / "CHANGELOG.md"
HEADER = "# Changelog\n\nAll notable changes to SkyAdmin Pro are documented here.\nFormat follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).\n\n"


class Commit(NamedTuple):
    subject: str
    category: str


def _run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        raise RuntimeError(stderr or f"git {' '.join(args)} failed")
    return (result.stdout or "").strip()


def latest_tag() -> str | None:
    try:
        tag = _run_git("describe", "--tags", "--abbrev=0", "--match", "v*")
    except RuntimeError:
        return None
    return tag or None


def tag_date(tag: str) -> str:
    try:
        raw = _run_git("log", "-1", "--format=%cs", tag)
        return raw or date.today().isoformat()
    except RuntimeError:
        return date.today().isoformat()


def categorize(subject: str) -> str:
    lowered = subject.lower()
    if lowered.startswith(("feat", "feature", "add ")):
        return "Added"
    if lowered.startswith(("fix", "bugfix", "hotfix")):
        return "Fixed"
    if lowered.startswith(("docs", "doc:")):
        return "Documentation"
    if lowered.startswith(("perf", "performance")):
        return "Performance"
    if lowered.startswith(("refactor", "split", "move ")):
        return "Changed"
    if lowered.startswith(("test", "ci", "build", "chore", "release")):
        return "Changed"
    return "Changed"


def normalize_subject(subject: str) -> str:
    text = subject.strip()
    text = re.sub(
        r"^(feat|feature|fix|docs|perf|refactor|test|ci|build|chore|release)(\([^)]+\))?:\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    if text and not text.endswith("."):
        text += "."
    return text


def commits_since(ref: str | None) -> list[Commit]:
    args = ["log", "--pretty=format:%s"]
    if ref:
        args.append(f"{ref}..HEAD")
    try:
        output = _run_git(*args)
    except RuntimeError:
        return []
    if not output:
        return []
    items: list[Commit] = []
    for line in output.splitlines():
        subject = line.strip()
        if not subject:
            continue
        if subject.lower().startswith("merge "):
            continue
        items.append(Commit(subject=normalize_subject(subject), category=categorize(subject)))
    return items


def group_commits(commits: list[Commit]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {
        "Added": [],
        "Changed": [],
        "Fixed": [],
        "Performance": [],
        "Documentation": [],
    }
    for commit in commits:
        grouped.setdefault(commit.category, []).append(commit.subject)
    return {key: values for key, values in grouped.items() if values}


def render_section(version: str, release_date: str, grouped: dict[str, list[str]]) -> str:
    lines = [f"## [{version}] - {release_date}", ""]
    if not grouped:
        lines.append("- Maintenance release.")
        lines.append("")
        return "\n".join(lines)
    for heading in ("Added", "Changed", "Fixed", "Performance", "Documentation"):
        items = grouped.get(heading) or []
        if not items:
            continue
        lines.append(f"### {heading}")
        lines.append("")
        for item in items:
            lines.append(f"- {item}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def read_changelog() -> str:
    if CHANGELOG.is_file():
        return CHANGELOG.read_text(encoding="utf-8")
    return HEADER + "## [Unreleased]\n\n"


def insert_version_section(text: str, version: str, section: str) -> str:
    if f"## [{version}]" in text:
        pattern = re.compile(rf"## \[{re.escape(version)}\][^\n]*\n.*?(?=\n## \[|\Z)", re.DOTALL)
        return pattern.sub(section.rstrip() + "\n\n", text, count=1)

    unreleased_marker = "## [Unreleased]"
    if unreleased_marker in text:
        return text.replace(unreleased_marker, section.rstrip() + "\n\n" + unreleased_marker, 1)

    if text.startswith("# Changelog"):
        parts = text.split("\n", 1)
        rest = parts[1] if len(parts) > 1 else ""
        return parts[0] + "\n\n" + section + rest.lstrip("\n")

    return HEADER + section + text


def clear_unreleased_entries(text: str) -> str:
    pattern = re.compile(r"(## \[Unreleased\]\n)(.*?)(?=\n## \[|\Z)", re.DOTALL)

    def repl(match: re.Match[str]) -> str:
        body = match.group(2).strip()
        if not body or body == "-":
            return match.group(1) + "\n"
        return match.group(0)

    return pattern.sub(repl, text, count=1)


def resolve_version(explicit: str) -> str:
    if explicit:
        return explicit.lstrip("v").strip()
    try:
        from skyadmin_pro.config import APP_VERSION

        return APP_VERSION
    except Exception:
        return date.today().isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate SkyAdmin Pro changelog content from git history")
    parser.add_argument("--version", default="", help="Release version (default: APP_VERSION)")
    parser.add_argument("--since", default="", help="Git ref to start from (default: latest v* tag)")
    parser.add_argument("--date", default="", help="Release date YYYY-MM-DD (default: tag date or today)")
    parser.add_argument("--write", action="store_true", help="Update CHANGELOG.md in the repo")
    parser.add_argument("--output", type=Path, default=None, help="Write release notes to a file")
    parser.add_argument("--print", dest="print_only", action="store_true", help="Print release notes to stdout")
    args = parser.parse_args()

    version = resolve_version(args.version)
    since = (args.since or "").strip() or latest_tag()
    release_date = (args.date or "").strip() or (tag_date(since) if since else date.today().isoformat())
    grouped = group_commits(commits_since(since))
    section = render_section(version, release_date, grouped)

    if args.write:
        text = read_changelog()
        text = insert_version_section(text, version, section)
        text = clear_unreleased_entries(text)
        if not text.startswith("# Changelog"):
            text = HEADER + text
        CHANGELOG.write_text(text, encoding="utf-8")
        print(f"Updated {CHANGELOG}")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(section, encoding="utf-8")
        print(f"Wrote {args.output}")

    if args.print_only or (not args.write and not args.output):
        print(section, end="")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
