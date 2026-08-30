"""Activation dialog regression tests."""

from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.services.license_authoring import generate_ed25519_license
from skyadmin_pro.ui.activation import ActivationDialog


def test_activation_dialog_accepts_generated_key(monkeypatch):
    """Local verify + save path should succeed without blocking on UI thread."""
    mid = "ABCD1234EFGH5678"
    monkeypatch.setattr("skyadmin_pro.services.license.get_machine_id", lambda: mid)
    monkeypatch.setattr("skyadmin_pro.services.license.requires_online_check", lambda: False)

    saved: list[str] = []

    def _fake_save(content: str):
        saved.append(content)

    monkeypatch.setattr("skyadmin_pro.services.license.save_license_file", _fake_save)

    app = ctk.CTk()
    app.withdraw()
    dialog = ActivationDialog(app, allow_quit=False)
    key = generate_ed25519_license(mid, days_valid=7, package_days=7)
    dialog.key_box.insert("1.0", key)
    dialog._activate()
    app.update_idletasks()
    app.destroy()

    assert saved, "license should be saved after successful activation"
    assert "Activation complete" in dialog.status.cget("text")
