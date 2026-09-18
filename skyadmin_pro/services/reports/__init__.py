"""Status report model — dashboard + tax snapshot, English-only, redaction-safe.

The model is plain data (dicts/lists/strings) so the PDF renderer stays dumb.
Every row is projected through an explicit allowlist; a runtime assert scan
rejects forbidden columns (mirrors export.FORBIDDEN_EXPORT_COLUMNS).
"""

from __future__ import annotations

from ._const_0 import REPORT_TABLE_ROW_CAP
from ._const_1 import _TAX_OVERVIEW_KEYS
from .funcs_0 import (  # noqa: F403
    FORBIDDEN_EXPORT_COLUMNS,
    _assert_no_forbidden,
    _cell,
    _project,
)
from .funcs_1 import (  # noqa: F403
    _TAX_OVERVIEW_KEYS,
    REPORT_TABLE_ROW_CAP,
    Database,
    Path,
    _assert_no_forbidden,
    _cell,
    _project,
    build_status_report,
    default_report_name,
    write_status_report_pdf,
)
