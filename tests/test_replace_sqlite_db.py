"""replace_sqlite_db retries Windows lock races."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from skyadmin_pro.db.replace_db import replace_sqlite_db


def test_replace_sqlite_db_retries_access_denied(tmp_path: Path) -> None:
    staged = tmp_path / "live.db.new"
    dest = tmp_path / "live.db"
    staged.write_bytes(b"new")
    dest.write_bytes(b"old")
    calls = {"n": 0}

    real_replace = __import__("os").replace

    def flaky(src, dst):
        calls["n"] += 1
        if calls["n"] < 3:
            err = PermissionError(13, "Access is denied")
            err.winerror = 5  # type: ignore[attr-defined]
            raise err
        return real_replace(src, dst)

    with patch("os.replace", side_effect=flaky):
        replace_sqlite_db(staged, dest, attempts=5)

    assert dest.read_bytes() == b"new"
    assert calls["n"] == 3


def test_replace_sqlite_db_rename_aside_fallback(tmp_path: Path) -> None:
    staged = tmp_path / "live.db.new"
    dest = tmp_path / "live.db"
    staged.write_bytes(b"new")
    dest.write_bytes(b"old")
    real_replace = __import__("os").replace

    def deny_direct(src, dst):
        src_s, dst_s = str(src), str(dst)
        # Deny only direct staged->dest; allow aside moves.
        if src_s.endswith(".new") and dst_s.endswith("live.db") and ".old_" not in dst_s:
            err = PermissionError(13, "Access is denied")
            err.winerror = 5  # type: ignore[attr-defined]
            raise err
        return real_replace(src, dst)

    with patch("os.replace", side_effect=deny_direct):
        replace_sqlite_db(staged, dest, attempts=10)

    assert dest.read_bytes() == b"new"


def test_replace_sqlite_db_gives_up(tmp_path: Path) -> None:
    staged = tmp_path / "live.db.new"
    dest = tmp_path / "live.db"
    staged.write_bytes(b"new")
    dest.write_bytes(b"old")

    def always_denied(src, dst):
        err = PermissionError(13, "Access is denied")
        err.winerror = 5  # type: ignore[attr-defined]
        raise err

    with (
        patch("os.replace", side_effect=always_denied),
        patch("skyadmin_pro.db.replace_db._try_overwrite_bytes", return_value=False),
        pytest.raises(PermissionError),
    ):
        replace_sqlite_db(staged, dest, attempts=3)
