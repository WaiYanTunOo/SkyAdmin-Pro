from __future__ import annotations

import logging
from pathlib import Path

from .chunk_3 import used_nonces


def _replace_control_file(path: Path, items: set[str]) -> None:
    current: set[str] = set()
    if path.exists():
        current = {ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()}
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


def banned_machines() -> frozenset[str]:
    """Machine IDs in ~/.skyadmin_pro/banned.txt — block entire machines."""
    try:
        from skyadmin_pro.paths import app_data_dir

        path = app_data_dir() / "banned.txt"
        if not path.exists():
            return frozenset()
        text = path.read_text(encoding="utf-8")
        return frozenset(t.strip().upper() for t in text.splitlines() if t.strip())
    except (OSError, ValueError):
        return frozenset()


def _parse_control_lines(text: str) -> tuple[list[str], list[str], list[str], list[str], tuple[str, str] | None]:
    revokes, bans, used, revoked_pcs = [], [], [], []
    latest = None
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
    return revokes, bans, used, revoked_pcs, latest


def revoked_passcodes() -> frozenset[str]:
    """Passcodes in ~/.skyadmin_pro/revoked_passcodes.txt — block individual passcodes."""
    try:
        from skyadmin_pro.paths import app_data_dir

        path = app_data_dir() / "revoked_passcodes.txt"
        if not path.exists():
            return frozenset()
        text = path.read_text(encoding="utf-8")
        return frozenset(t.strip() for t in text.splitlines() if t.strip())
    except (OSError, ValueError):
        return frozenset()


def _control_paths() -> tuple[Path, Path, Path] | None:
    try:
        from skyadmin_pro.paths import app_data_dir

        base = app_data_dir()
        return base / "revoked.txt", base / "banned.txt", base / "revoked_passcodes.txt"
    except (ImportError, OSError):
        return None


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
        logging.getLogger(__name__).warning("Failed to burn nonce %s", nonce, exc_info=True)
