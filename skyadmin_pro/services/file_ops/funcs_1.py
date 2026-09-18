from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

from .funcs_0 import sanitize_token


def build_invoice_filename(
    *,
    client_name: str,
    suffix: str,
    invoice_no: str = "",
    today: date | None = None,
) -> str:
    """SOP invoice naming: 202608_ClientName_Invoice_INV20260801.pdf"""
    day = today or date.today()
    stamp = day.strftime("%Y%m")
    number = invoice_no.strip()
    if number:
        if not number.upper().startswith("INV"):
            number = f"INV{number}"
    else:
        number = f"INV{stamp}01"
    ext = suffix if suffix.startswith(".") else f".{suffix}"
    return "_".join([stamp, sanitize_token(client_name), "Invoice", number]) + ext.lower()


def unique_path(destination: Path) -> Path:
    if not destination.exists():
        return destination
    stem, suffix, parent = destination.stem, destination.suffix, destination.parent
    index = 2
    while True:
        candidate = parent / f"{stem}_{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def list_files(folder: Path) -> list[Path]:
    try:
        if not folder.exists():
            return []
        files = [path for path in folder.iterdir() if path.is_file() and not path.name.startswith(".")]
    except OSError:
        # Folder removed mid-scan, permission denied, or long-path failure.
        return []
    return sorted(files, key=lambda item: item.name.lower())


def list_files_with_signature(
    folder: Path,
) -> tuple[list[Path], tuple[tuple[str, int, float], ...]]:
    """Single directory walk returning files plus their change signature."""
    files = list_files(folder)
    signature: list[tuple[str, int, float]] = []
    for path in files:
        try:
            stats = path.stat()
        except OSError:
            continue
        signature.append((path.name, stats.st_size, stats.st_mtime))
    return files, tuple(signature)


def file_signature(folder: Path) -> tuple[tuple[str, int, float], ...]:
    return list_files_with_signature(folder)[1]


def move_file(source: Path, dest_dir: Path, new_name: str | None = None) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = unique_path(dest_dir / (new_name or source.name))
    shutil.move(str(source), str(target))
    return target


def backup_file(source: Path, backup_dir: Path) -> Path:
    """Copy a file into a backup directory, keeping the original in place."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    target = unique_path(backup_dir / source.name)
    shutil.copy2(str(source), str(target))
    return target


def copy_file(source: Path, dest_dir: Path, new_name: str | None = None) -> Path:
    """Copy a file into a directory, keeping the original in place."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = unique_path(dest_dir / (new_name or source.name))
    shutil.copy2(str(source), str(target))
    return target
