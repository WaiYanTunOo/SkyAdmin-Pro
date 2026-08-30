"""Lightweight performance guards for large client lists."""

import time

import pytest

from skyadmin_pro.database import Database


@pytest.fixture
def populated_db(tmp_path) -> Database:
    db = Database(tmp_path / "perf.db")
    with db.connection() as conn:
        conn.executemany(
            "INSERT INTO clients (name, contact_name, email, status) VALUES (?, ?, ?, ?)",
            [(f"Client {index:04d}", f"Contact {index}", f"c{index}@example.com", "active") for index in range(500)],
        )
    return db


def test_search_clients_handles_five_hundred_rows(populated_db):
    start = time.perf_counter()
    rows = populated_db.search_clients("")
    elapsed = time.perf_counter() - start
    assert len(rows) == 500
    assert elapsed < 0.75


def test_list_client_names_handles_five_hundred_rows(populated_db):
    start = time.perf_counter()
    names = populated_db.list_client_names()
    elapsed = time.perf_counter() - start
    assert len(names) == 500
    assert elapsed < 0.5
