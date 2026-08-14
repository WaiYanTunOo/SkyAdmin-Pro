"""Document pipeline: rename/move, image-to-PDF, merge, and monthly archive."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from skyadmin_pro.config import (
    DOC_TYPE_PASSPORT_VISA,
    IMAGE_SUFFIXES,
    PDF_SUFFIX,
)
from skyadmin_pro.paths import WorkspacePaths

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
    if not folder.exists():
        return []
    files = [
        path
        for path in folder.iterdir()
        if path.is_file() and not path.name.startswith(".")
    ]
    return sorted(files, key=lambda item: item.name.lower())


def file_signature(folder: Path) -> tuple[tuple[str, int, float], ...]:
    signature: list[tuple[str, int, float]] = []
    for path in list_files(folder):
        try:
            stats = path.stat()
        except OSError:
            continue
        signature.append((path.name, stats.st_size, stats.st_mtime))
    return tuple(signature)


def move_file(source: Path, dest_dir: Path, new_name: str | None = None) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = unique_path(dest_dir / (new_name or source.name))
    shutil.move(str(source), str(target))
    return target


def open_in_file_manager(path: Path) -> None:
    resolved = path.resolve()
    if sys.platform == "win32":
        os.startfile(resolved)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(resolved)])
    else:
        subprocess.Popen(["xdg-open", str(resolved)])


def _as_rgb(image):
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
    rgb_images = []
    try:
        for path in image_paths:
            with Image.open(path) as raw:
                rgb_images.append(_as_rgb(raw).copy())

        outputs: list[Path] = []
        if combine:
            stamp = date.today().strftime("%Y%m%d")
            name = combined_name or f"{stamp}_Images.pdf"
            if not name.lower().endswith(PDF_SUFFIX):
                name += PDF_SUFFIX
            output = unique_path(dest_dir / name)
            first, rest = rgb_images[0], rgb_images[1:]
            first.save(output, "PDF", resolution=150.0, save_all=True, append_images=rest)
            outputs.append(output)
        else:
            for path, image in zip(image_paths, rgb_images):
                output = unique_path(dest_dir / f"{path.stem}.pdf")
                image.save(output, "PDF", resolution=150.0)
                outputs.append(output)
        return outputs
    finally:
        for image in rgb_images:
            image.close()


def merge_pdfs(sources: list[Path], output: Path) -> Path:
    from PyPDF2 import PdfReader, PdfWriter

    if not sources:
        raise ValueError("Select at least one PDF to merge.")

    writer = PdfWriter()
    for source in sources:
        reader = PdfReader(str(source))
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
