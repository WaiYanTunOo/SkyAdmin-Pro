"""Client workspace folder resolution and repair."""

from pathlib import Path

import pytest

from skyadmin_pro.services.workflow import (
    client_folder_key,
    create_client_workspace,
    repair_client_workspaces,
    resolve_client_folder,
    sanitize_folder_name,
)


def test_client_folder_key_ignores_slash_and_spacing():
    a = "ATH General Trading Co.,Ltd/บริษัท เอทีเอช จีเนอรัล เทรดดิ้ง จำกัด"
    b = "ATH General Trading Co.,Ltdบริษัท เอทีเอช จีเนอรัล เทรดดิ้ง จำกัด"
    assert client_folder_key(a) == client_folder_key(b)
    assert sanitize_folder_name(a) == sanitize_folder_name(b)


def test_resolve_client_folder_links_existing_legacy_folder(tmp_path):
    clients_root = tmp_path / "Clients"
    clients_root.mkdir()
    legacy_name = "ATH General Trading Co.,Ltdบริษัท เอทีเอช"
    (clients_root / legacy_name).mkdir()
    db_name = "ATH General Trading Co.,Ltd/บริษัท เอทีเอช"
    folder = resolve_client_folder(clients_root, db_name, create=True)
    assert folder.name == legacy_name
    assert (folder / "01_Company_Setup").is_dir()


def test_create_client_workspace_is_idempotent(tmp_path):
    clients_root = tmp_path / "Clients"
    name = "Beta Co/Ltd"
    first = create_client_workspace(clients_root, name)
    second = create_client_workspace(clients_root, name)
    assert first == second
    assert (first / "04_Financial_Docs" / "Invoices").is_dir()


def test_repair_client_workspaces_creates_missing(tmp_path):
    clients_root = tmp_path / "Clients"
    clients_root.mkdir()
    names = ["Existing Co", "New Client Ltd."]
    (clients_root / sanitize_folder_name(names[0])).mkdir()
    result = repair_client_workspaces(clients_root, names)
    assert result["total"] == 2
    assert result["created"] == 1
    assert (clients_root / sanitize_folder_name(names[1]) / "02_Accounting").is_dir()


def test_resolve_client_folder_raises_when_missing(tmp_path):
    clients_root = tmp_path / "Clients"
    clients_root.mkdir()
    with pytest.raises(FileNotFoundError):
        resolve_client_folder(clients_root, "Missing Co", create=False)
