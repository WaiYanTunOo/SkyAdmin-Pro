from __future__ import annotations

import os
import subprocess
import sys
from datetime import date
from pathlib import Path

from skyadmin_pro.config import PDF_SUFFIX

from ._const_0 import logger
from ._const_4 import _BLOCKED_OPEN_SUFFIXES
from .funcs_1 import unique_path


def open_in_file_manager(path: Path) -> None:
    resolved = path.resolve()
    if not resolved.exists():
        raise RuntimeError(f"Path does not exist: {resolved}")
    if resolved.is_file() and resolved.suffix.lower() in _BLOCKED_OPEN_SUFFIXES:
        raise RuntimeError(f"Refusing to open executable file type: {resolved.suffix}")
    if not resolved.is_file() and not resolved.is_dir():
        raise RuntimeError(f"Not a file or folder: {resolved}")
    logger.info("Opening in file manager: %s", resolved)
    try:
        if sys.platform == "win32":
            os.startfile(resolved)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "--", str(resolved)])
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
                except OSError:
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
