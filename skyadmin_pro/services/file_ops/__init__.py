"""Document pipeline: rename/move, image-to-PDF, merge, and monthly archive."""

from __future__ import annotations

from dataclasses import dataclass

from ._const_0 import annotations, logger, logging  # noqa: F403
from ._const_1 import _UNSAFE_CHARS, annotations, re  # noqa: F403
from ._const_2 import _WHITESPACE, annotations, re  # noqa: F403
from ._const_3 import _AMOUNT_KEEP, annotations, re  # noqa: F403
from ._const_4 import _BLOCKED_OPEN_SUFFIXES, annotations  # noqa: F403
from .archiveResultMixin0 import ArchiveResultMixin0


@dataclass
class ArchiveResult(ArchiveResultMixin0):
    pass


from .funcs_0 import (  # noqa: F403
    _AMOUNT_KEEP,
    _UNSAFE_CHARS,
    _WHITESPACE,
    DOC_TYPE_PASSPORT_VISA,
    annotations,
    build_smart_filename,
    compact_date,
    date,
    datetime,
    filename_type_token,
    format_thousands,
    parse_flexible_date,
    sanitize_amount,
    sanitize_token,
)
from .funcs_1 import (  # noqa: F403
    Path,
    annotations,
    backup_file,
    build_invoice_filename,
    copy_file,
    date,
    file_signature,
    list_files,
    list_files_with_signature,
    move_file,
    sanitize_token,
    shutil,
    unique_path,
)
from .funcs_2 import (  # noqa: F403
    _BLOCKED_OPEN_SUFFIXES,
    PDF_SUFFIX,
    Path,
    _as_rgb,
    annotations,
    date,
    images_to_pdf,
    open_in_file_manager,
    os,
    subprocess,
    sys,
    unique_path,
)
from .funcs_3 import (  # noqa: F403
    IMAGE_SUFFIXES,
    ArchiveResult,
    Path,
    WorkspacePaths,
    _move_all,
    annotations,
    archive_ready_and_clean_staging,
    date,
    is_image,
    merge_pdfs,
    month_archive_folder,
    shutil,
    unique_path,
)
from .funcs_4 import PDF_SUFFIX, Path, annotations, is_pdf  # noqa: F403
