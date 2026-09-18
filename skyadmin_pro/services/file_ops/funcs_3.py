from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

from skyadmin_pro.config import IMAGE_SUFFIXES
from skyadmin_pro.paths import WorkspacePaths

from . import ArchiveResult
from .funcs_1 import unique_path


def merge_pdfs(sources: list[Path], output: Path) -> Path:
    from pypdf import PdfReader, PdfWriter

    if not sources:
        raise ValueError("Select at least one PDF to merge.")

    writer = PdfWriter()
    readers: list[PdfReader] = []
    try:
        for source in sources:
            reader = PdfReader(str(source))
            readers.append(reader)
            if getattr(reader, "is_encrypted", False):
                try:
                    reader.decrypt("")
                except (
                    OSError,
                    ValueError,
                    KeyError,
                ) as exc:  # defensive: pypdf decrypt failure — normalize to a user-facing error
                    raise RuntimeError(f"Cannot read encrypted PDF: {source.name}") from exc
            for page in reader.pages:
                writer.add_page(page)

        output.parent.mkdir(parents=True, exist_ok=True)
        final_path = unique_path(output)
        with final_path.open("wb") as handle:
            writer.write(handle)
        return final_path
    finally:
        # Close readers FIRST: on Windows they hold the source files locked
        # until GC otherwise, breaking a following move/archive of those PDFs.
        for reader in readers:
            stream = getattr(reader, "stream", None)
            if stream is not None:
                try:
                    stream.close()
                except OSError:
                    pass
        try:
            writer.close()
        except OSError:
            pass


def month_archive_folder(archive_root: Path, when: date | None = None) -> Path:
    stamp = when or date.today()
    months = (
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    )
    return archive_root / f"{months[stamp.month - 1]}_{stamp.year}"


def _move_all(source_dir: Path, dest_dir: Path) -> tuple[list[str], list[str]]:
    moved: list[str] = []
    errors: list[str] = []
    dest_dir.mkdir(parents=True, exist_ok=True)
    for item in list(source_dir.iterdir()) if source_dir.exists() else []:
        if item.name.startswith("."):
            continue
        try:
            target = unique_path(dest_dir / item.name)
            shutil.move(str(item), str(target))
            moved.append(target.name)
        except OSError as exc:
            errors.append(f"{item.name}: {exc}")
    return moved, errors


def archive_ready_and_clean_staging(paths: WorkspacePaths) -> ArchiveResult:
    """Move Ready-to-Upload files into Z_Archive_Backup/Month_Year and empty staging."""
    folder = month_archive_folder(paths.archive)
    result = ArchiveResult(month_folder=folder)
    ready, ready_errors = _move_all(paths.ready_to_upload, folder)
    staging, staging_errors = _move_all(paths.staging, folder)
    result.moved_ready = ready
    result.moved_staging = staging
    result.errors = ready_errors + staging_errors
    return result


def is_image(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_SUFFIXES
