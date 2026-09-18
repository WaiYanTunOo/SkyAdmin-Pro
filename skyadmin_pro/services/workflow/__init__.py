"""Workflow automation: portal upload, client onboarding, and EOD reports."""

from __future__ import annotations

from ._const_0 import _RESERVED, annotations, re  # noqa: F403
from ._const_1 import _WIN_DEVICES, annotations, re  # noqa: F403
from .funcs_0 import (  # noqa: F403
    _RESERVED,
    _WIN_DEVICES,
    CLIENT_WORKSPACE_FOLDERS,
    FINANCIAL_DOC_FOLDER_MAP,
    Path,
    _ensure_workspace_subfolders,
    _index_client_folders,
    annotations,
    client_folder_key,
    create_client_workspace,
    re,
    resolve_client_folder,
    sanitize_folder_name,
)
from .funcs_1 import (  # noqa: F403
    DEFAULT_PORTAL_URL,
    Path,
    _index_client_folders,
    annotations,
    client_folder_key,
    copy_to_clipboard,
    create_client_workspace,
    normalize_portal_url,
    open_portal_and_copy_path,
    repair_client_workspaces,
    sanitize_folder_name,
    urlparse,
    webbrowser,
)
from .funcs_2 import annotations, date, format_eod_report  # noqa: F403
