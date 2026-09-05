"""Export visible-columns-only — opt-in restriction, never silent emptying."""

from __future__ import annotations

import openpyxl

from skyadmin_pro.services.export import export_to_excel


def _seed(db) -> None:
    with db.connection() as conn:
        conn.executemany(
            "INSERT INTO clients (name, contact_name, email, status) VALUES (?, ?, ?, ?)",
            [("Export Co", "C. Person", "e@x.io", "active")],
        )


def _sheet_headers(path, sheet: str) -> list:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb[sheet]
        return [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
    finally:
        wb.close()


def test_default_export_ignores_hidden_state(db, tmp_path):
    """Default (visible_only=None) exports complete sheets."""
    _seed(db)
    dest = tmp_path / "full.xlsx"
    export_to_excel(db, dest)
    headers = _sheet_headers(dest, "Clients")
    assert "Company name" in headers
    assert "Email" in headers
    assert "Contact" in headers


def test_visible_only_restricts_sheet(db, tmp_path):
    _seed(db)
    dest = tmp_path / "slim.xlsx"
    export_to_excel(db, dest, visible_only={"Clients": ["name", "email"]})
    headers = _sheet_headers(dest, "Clients")
    assert "Company name" in headers
    assert "Email" in headers
    assert "Contact" not in headers


def test_visible_only_never_empties_sheet(db, tmp_path):
    _seed(db)
    dest = tmp_path / "fallback.xlsx"
    export_to_excel(db, dest, visible_only={"Clients": ["no_such_field"]})
    headers = _sheet_headers(dest, "Clients")
    assert "Company name" in headers  # fell back to complete mapping


def test_visible_only_other_sheets_complete(db, tmp_path):
    _seed(db)
    dest = tmp_path / "mixed.xlsx"
    export_to_excel(db, dest, visible_only={"Clients": ["name"]})
    assert "Title" in _sheet_headers(dest, "Tasks")
