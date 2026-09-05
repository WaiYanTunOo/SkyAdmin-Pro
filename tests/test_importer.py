"""Tests for CSV importer — validate, deduplicate, batch insert."""

from __future__ import annotations

import csv
import tempfile
from pathlib import Path

from skyadmin_pro.services.importer import import_clients_from_csv


def _make_csv(tmp_path: Path, rows: list[dict], filename: str = "clients.csv") -> Path:
    path = tmp_path / filename
    if not rows:
        path.write_text("name,company_name,email,status\n", encoding="utf-8")
        return path
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


class TestImporter:
    def test_valid_csv(self, tmp_path, db):
        csv_path = _make_csv(tmp_path, [
            {"name": "Acme Corp", "company_name": "Acme", "email": "test@acme.com", "status": "active"},
            {"name": "Beta Inc", "company_name": "Beta", "email": "info@beta.com", "status": "inactive"},
        ])
        stats = import_clients_from_csv(db, csv_path)
        assert stats["imported"] == 2
        assert stats["skipped"] == 0
        assert stats["errors"] == 0

    def test_deduplication(self, tmp_path, db):
        # First import
        csv_path = _make_csv(tmp_path, [
            {"name": "Acme Corp", "company_name": "Acme"},
        ])
        import_clients_from_csv(db, csv_path)
        # Second import same name
        stats = import_clients_from_csv(db, csv_path)
        assert stats["skipped"] == 1
        assert stats["imported"] == 0

    def test_missing_name_column(self, tmp_path, db):
        csv_path = _make_csv(tmp_path, [{"company_name": "Acme"}])
        stats = import_clients_from_csv(db, csv_path)
        assert stats["errors"] == 1

    def test_empty_name_row(self, tmp_path, db):
        csv_path = _make_csv(tmp_path, [{"name": "", "company_name": "Acme"}])
        stats = import_clients_from_csv(db, csv_path)
        assert stats["errors"] == 1

    def test_bad_encoding(self, tmp_path, db):
        csv_path = tmp_path / "bad.csv"
        csv_path.write_bytes(b"\xff\xfe\x00\x01name\n")
        stats = import_clients_from_csv(db, csv_path)
        # Should handle gracefully (either import or error, not crash)
        assert isinstance(stats, dict)

    def test_empty_file(self, tmp_path, db):
        csv_path = tmp_path / "empty.csv"
        csv_path.write_text("", encoding="utf-8")
        stats = import_clients_from_csv(db, csv_path)
        assert stats["errors"] == 1

    def test_optional_columns(self, tmp_path, db):
        csv_path = _make_csv(tmp_path, [
            {"name": "Acme Corp", "director": "John", "contact_number": "081-234-5678"},
        ])
        stats = import_clients_from_csv(db, csv_path)
        assert stats["imported"] == 1
