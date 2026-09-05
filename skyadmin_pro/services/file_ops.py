"""Document pipeline: rename/move, image-to-PDF, merge, and monthly archive."""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image

from skyadmin_pro.config import (
    DOC_TYPE_PASSPORT_VISA,
    IMAGE_SUFFIXES,
    PDF_SUFFIX,
)
from skyadmin_pro.paths import WorkspacePaths

logger = logging.getLogger(__name__)

_UNSAFE_CHARS = re.compile(r'[<>:"/\\|?*]+')
_WHITESPACE = re.compile(r"\s+")
_AMOUNT_KEEP = re.compile(r"[^\d.]")


def sanitize_token(value: str) -> str:
    """Make a filesystem-safe filename fragment (spaces removed, no reserved chars)."""
    cleaned = _UNSAFE_CHARS.sub("-", value.strip())
    cleaned = _WHITESPACE.sub("", cleaned)
    cleaned = cleaned.strip("._-")
    return cleaned or "Unknown"


def sanitize_amount(value: str) -> str:
    cleaned = _AMOUNT_KEEP.sub("", value.strip().replace(",", ""))
    return cleaned or sanitize_token(value)


def format_thousands(value: str) -> str:
    """Group the integer part of an amount with thousands separators for display.

    Leaves the value untouched when it is empty or not a plain number, and
    keeps at most two decimal places.
    """
    stripped = value.strip().replace(",", "")
    if not stripped:
        return value
    cleaned = _AMOUNT_KEEP.sub("", stripped)
    if not cleaned:
        return value
    if "." in cleaned:
        integer_part, decimal_part = cleaned.split(".", 1)
    else:
        integer_part, decimal_part = cleaned, ""
    try:
        grouped = f"{int(integer_part):,}" if integer_part else ""
    except ValueError:
        return value
    result = grouped + (f".{decimal_part[:2]}" if decimal_part else "")
    return result or value


def parse_flexible_date(value: str) -> str | None:
    """Return ISO YYYY-MM-DD, or None if the value cannot be parsed."""
    text = value.strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y%m%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def compact_date(iso_date: str) -> str:
    return iso_date.replace("-", "")


def filename_type_token(document_type: str) -> str:
    if document_type == DOC_TYPE_PASSPORT_VISA:
        return "Passport"
    return sanitize_token(document_type)


def build_smart_filename(
    *,
    client_name: str,
    document_type: str,
    suffix: str,
    expiry_iso: str | None = None,
    amount: str | None = None,
    today: date | None = None,
) -> str:
    stamp = (today or date.today()).strftime("%Y%m%d")
    parts = [stamp, sanitize_token(client_name), filename_type_token(document_type)]
    if expiry_iso:
        parts.append(compact_date(expiry_iso))
    if amount:
        parts.append(sanitize_amount(amount))
    ext = suffix if suffix.startswith(".") else f".{suffix}"
    return "_".join(parts) + ext.lower()


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


def open_in_file_manager(path: Path) -> None:
    resolved = path.resolve()
    if not resolved.exists():
        raise RuntimeError(f"Path does not exist: {resolved}")
    logger.info("Opening in file manager: %s", resolved)
    try:
        if sys.platform == "win32":
            os.startfile(resolved)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(resolved)])
        else:
            subprocess.Popen(["xdg-open", str(resolved)])
    except OSError as exc:
        raise RuntimeError(f"Could not open folder: {resolved}") from exc


def _as_rgb(image: Image.Image) -> Image.Image:
    from PIL import Image

    if image.mode == "RGB":
        return image
    if image.mode in {"RGBA", "LA"} or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.split()[-1])
        return background
    return image.convert("RGB")


def images_to_pdf(
    image_paths: list[Path],
    dest_dir: Path,
    *,
    combine: bool = False,
    combined_name: str | None = None,
) -> list[Path]:
    from PIL import Image

    if not image_paths:
        raise ValueError("No images to convert.")

    dest_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    if combine:
        # Combined PDFs need every page open at once (PIL writes all pages in
        # one save call) — collect frames, save, then release.
        stamp = date.today().strftime("%Y%m%d")
        name = combined_name or f"{stamp}_Images.pdf"
        if not name.lower().endswith(PDF_SUFFIX):
            name += PDF_SUFFIX
        output = unique_path(dest_dir / name)
        rgb_images = []
        try:
            for path in image_paths:
                with Image.open(path) as raw:
                    rgb_images.append(_as_rgb(raw).copy())
            first, rest = rgb_images[0], rgb_images[1:]
            first.save(output, "PDF", resolution=150.0, save_all=True, append_images=rest)
            outputs.append(output)
        finally:
            for image in rgb_images:
                try:
                    image.close()
                except Exception:
                    pass
        return outputs
    # Single-file mode: one image in memory at a time.
    for path in image_paths:
        output = unique_path(dest_dir / f"{path.stem}.pdf")
        with Image.open(path) as raw:
            rgb = _as_rgb(raw).copy()
        try:
            rgb.save(output, "PDF", resolution=150.0)
        finally:
            rgb.close()
        outputs.append(output)
    return outputs


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
                except Exception as exc:
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
                except Exception:
                    pass
        try:
            writer.close()
        except Exception:
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


@dataclass
class ArchiveResult:
    month_folder: Path
    moved_ready: list[str] = field(default_factory=list)
    moved_staging: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def total_moved(self) -> int:
        return len(self.moved_ready) + len(self.moved_staging)


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


def is_pdf(path: Path) -> bool:
    return path.suffix.lower() == PDF_SUFFIX
