"""Supplier Services company/service fields are related dropdowns."""

from __future__ import annotations

from pathlib import Path


def _pkg_text(*parts: str) -> str:
    root = Path(__file__).resolve().parents[1].joinpath(*parts)
    if root.is_file():
        return root.read_text(encoding="utf-8")
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(root.rglob("*.py")))


def test_supplier_services_use_client_and_service_combos():
    src = _pkg_text("skyadmin_pro", "ui", "views", "database_tasks", "suppliers", "services_tab")
    assert "list_client_names" in src
    assert "list_service_types" in src
    assert 'state="readonly"' in src
    assert "CTkComboBox" in src
    assert 'placeholder_text="Company name"' not in src
    assert "_refresh_svc_combos" in src
