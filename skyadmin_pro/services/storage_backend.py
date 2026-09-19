"""Attachment storage seam — local filesystem today, Drive when configured.

Owner-operator milestone stays offline-first. Google Drive slots in as a
second ``StorageBackend`` behind :func:`get_storage_backend`. PDF bytes
never go through the Worker (Plane B).
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class NotConfiguredError(RuntimeError):
    """Raised when a cloud backend is selected but OAuth is missing."""


class StorageBackend(Protocol):
    """Minimal surface a cloud store must implement to replace local disk."""

    def save_bytes(self, relpath: str, data: bytes) -> Path: ...
    def read_bytes(self, relpath: str) -> bytes: ...
    def delete(self, relpath: str) -> bool: ...
    def exists(self, relpath: str) -> bool: ...
    def list_rel(self, prefix: str = "") -> list[str]: ...


class LocalStorageBackend:
    """Filesystem backend confined under ``root`` (traversal-safe)."""

    def __init__(self, root: Path | str) -> None:
        self._root = Path(root).resolve()

    def _resolve(self, relpath: str) -> Path:
        candidate = (self._root / Path(relpath)).resolve()
        if candidate != self._root and self._root not in candidate.parents:
            raise ValueError(f"Path escapes storage root: {relpath!r}")
        return candidate

    def save_bytes(self, relpath: str, data: bytes) -> Path:
        dest = self._resolve(relpath)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return dest

    def read_bytes(self, relpath: str) -> bytes:
        return self._resolve(relpath).read_bytes()

    def delete(self, relpath: str) -> bool:
        try:
            self._resolve(relpath).unlink()
            return True
        except FileNotFoundError:
            return False

    def exists(self, relpath: str) -> bool:
        return self._resolve(relpath).exists()

    def list_rel(self, prefix: str = "") -> list[str]:
        base = self._resolve(prefix) if prefix else self._root
        if not base.exists():
            return []
        if base.is_file():
            return [base.relative_to(self._root).as_posix()]
        return sorted(p.relative_to(self._root).as_posix() for p in base.rglob("*") if p.is_file())


def get_storage_backend(root: Path | str | None = None, db=None):
    """Return Drive when entitled+connected; otherwise local workspace."""
    if root is None:
        from skyadmin_pro.paths import default_workspace_root

        root = default_workspace_root()
    if db is not None:
        try:
            from skyadmin_pro.services.drive.entitlement import (
                drive_preference_on,
                license_allows_drive,
            )
            from skyadmin_pro.services.drive.tokens import load_refresh_token

            if license_allows_drive(db) and drive_preference_on(db) and load_refresh_token(db):
                from skyadmin_pro.services.drive.backend import GoogleDriveStorageBackend

                return GoogleDriveStorageBackend(db)
        except Exception as e:
            import logging

            logging.getLogger(__name__).error("Drive backend unavailable, falling back to local: %s", e)
    return LocalStorageBackend(root)


__all__ = [
    "LocalStorageBackend",
    "NotConfiguredError",
    "StorageBackend",
    "get_storage_backend",
]
