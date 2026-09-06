"""Attachment storage seam — local filesystem today, cloud later.

Owner-operator milestone stays offline-first: every call below hits the
local workspace. When Google Drive (or another cloud store) is added, it
slots in as a second ``StorageBackend`` implementation behind
:func:`get_storage_backend` — views must keep talking to the interface,
never to ``pathlib``/``shutil`` directly for *new* attachment code.

Sync-metadata discipline for future cloud push (no migration of old rows):
new/updated records already stamp ``updated_at`` via ``Database._now()``
and carry a stable ``global_id`` (see ``CoreMixin._backfill_sync_global_ids``).
A future push worker can order by ``(updated_at, id)`` and key by
``global_id`` — nothing in this module changes write paths today.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


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


def get_storage_backend(root: Path | str | None = None) -> LocalStorageBackend:
    """Return the active backend. ``root=None`` uses the workspace root.

    The ``backend=`` selection hook (env/config) for a Drive backend gets
    added with the cloud milestone — the signature already returns the
    ``StorageBackend`` interface so callers won't change.
    """
    if root is None:
        from skyadmin_pro.paths import default_workspace_root

        root = default_workspace_root()
    return LocalStorageBackend(root)


__all__ = [
    "LocalStorageBackend",
    "StorageBackend",
    "get_storage_backend",
]
