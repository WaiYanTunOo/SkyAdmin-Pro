"""Local filesystem layout for SkyAdmin Pro.

The workspace root defaults to Documents/SkyAdmin Pro and can be changed
later from Settings. All document-pipeline folders live under that root.
"""

from __future__ import annotations

from pathlib import Path

from skyadmin_pro.config import (
    APP_NAME,
    FOLDER_ARCHIVE,
    FOLDER_CLIENTS,
    FOLDER_READY,
    FOLDER_STAGING,
)


def user_documents_dir() -> Path:
    """Return the platform Documents folder, falling back to the home directory."""
    home = Path.home()
    documents = home / "Documents"
    return documents if documents.exists() else home


def default_workspace_root() -> Path:
    return user_documents_dir() / APP_NAME


def app_data_dir() -> Path:
    """Directory that holds the SQLite database (next to the workspace, under home)."""
    path = Path.home() / ".skyadmin_pro"
    path.mkdir(parents=True, exist_ok=True)
    return path


def database_path() -> Path:
    return app_data_dir() / "skyadmin_pro.db"


class WorkspacePaths:
    """Resolved paths for the document pipeline. Call ensure() after construction."""

    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root) if root else default_workspace_root()

    @property
    def staging(self) -> Path:
        return self.root / FOLDER_STAGING

    @property
    def ready_to_upload(self) -> Path:
        return self.root / FOLDER_READY

    @property
    def archive(self) -> Path:
        return self.root / FOLDER_ARCHIVE

    @property
    def clients(self) -> Path:
        return self.root / FOLDER_CLIENTS

    def ensure(self) -> None:
        """Create the workspace root and standard pipeline folders if missing."""
        for folder in (
            self.root,
            self.staging,
            self.ready_to_upload,
            self.archive,
            self.clients,
        ):
            folder.mkdir(parents=True, exist_ok=True)
