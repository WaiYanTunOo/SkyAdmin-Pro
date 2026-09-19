"""Client portal logins: edit in Company Details; Office Hub is read-only."""

from __future__ import annotations

from pathlib import Path


def _pkg_text(*parts: str) -> str:
    root = Path(__file__).resolve().parents[1].joinpath(*parts)
    if root.is_file():
        return root.read_text(encoding="utf-8")
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(root.rglob("*.py")))


def test_tax_ids_owns_client_credential_crud():
    tax = _pkg_text("skyadmin_pro", "ui", "views", "company_details", "tax_ids_tab")
    assert "Edit in Office Hub" not in tax
    assert "_save_client_cred" in tax
    assert "_delete_client_cred" in tax
    assert "_new_client_cred" in tax
    assert "add_client_credential" in tax
    assert "Client portal logins (read-only)" not in tax


def test_office_hub_clients_login_data_is_readonly():
    vault = _pkg_text("skyadmin_pro", "ui", "views", "office_hub", "vault_tab")
    assert 'CLIENTS_LOGIN_TAB = "Clients Login Data"' in vault
    assert "Client DBD / RD" not in vault
    assert "_save_client_credential" not in vault
    assert "_delete_client_credential" not in vault
    assert "_new_client_credential" not in vault
    assert "Open Company Details" in vault
    assert 'state="disabled"' in vault


def test_i18n_clients_login_data_keys():
    i18n = _pkg_text("skyadmin_pro", "services", "i18n.py")
    assert '"Clients Login Data"' in i18n
