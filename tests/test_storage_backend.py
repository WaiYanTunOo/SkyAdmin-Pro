"""StorageBackend seam — local impl round-trip + traversal guard."""

from __future__ import annotations

import pytest

from skyadmin_pro.services.storage_backend import get_storage_backend


def test_local_backend_round_trip(tmp_path):
    store = get_storage_backend(tmp_path)
    dest = store.save_bytes("Clients/Acme/note.txt", b"hello")
    assert dest.exists()
    assert store.read_bytes("Clients/Acme/note.txt") == b"hello"
    assert store.exists("Clients/Acme/note.txt")
    assert store.list_rel("Clients") == ["Clients/Acme/note.txt"]
    assert store.delete("Clients/Acme/note.txt") is True
    assert store.delete("Clients/Acme/note.txt") is False


def test_local_backend_rejects_traversal(tmp_path):
    store = get_storage_backend(tmp_path)
    with pytest.raises(ValueError):
        store.save_bytes("../escape.txt", b"x")
    with pytest.raises(ValueError):
        store.read_bytes("../../etc/passwd")
