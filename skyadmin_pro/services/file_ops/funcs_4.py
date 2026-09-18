from __future__ import annotations

from pathlib import Path

from skyadmin_pro.config import PDF_SUFFIX


def is_pdf(path: Path) -> bool:
    return path.suffix.lower() == PDF_SUFFIX
