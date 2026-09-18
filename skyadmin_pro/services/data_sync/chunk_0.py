from __future__ import annotations

from ._common import *
from ._common import Path, find_license_file, getpass, logger


def _credentials_path() -> Path:
    from skyadmin_pro.paths import app_data_dir

    return app_data_dir() / "sync_device.json"


def save_sync_credentials(machine_id: str, sync_token: str) -> None:
    from skyadmin_pro.services.secret_fields import encrypt_secret

    path = _credentials_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        {"machine_id": machine_id.strip().upper(), "sync_token": sync_token.strip()}, ensure_ascii=False
    )
    path.write_text(encrypt_secret(payload), encoding="utf-8")
    try:
        path.chmod(384)
    except OSError as exc:
        logger.warning("Could not chmod %s: %s", path, exc)
    if sys.platform == "win32":
        try:
            import subprocess

            user = os.environ.get("USERNAME") or getpass.getuser()
            resolved_path = str(path)
            if not os.path.exists(resolved_path):
                return
            subprocess.run(
                ["icacls", resolved_path, "/inheritance:r", "/grant:r", f"{user}:(F)"], capture_output=True, timeout=5
            )
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            logger.warning("Could not restrict ACL on %s: %s", path, exc)


def load_sync_credentials() -> tuple[str, str] | None:
    path = _credentials_path()
    if not path.exists():
        return None
    try:
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return None
        from skyadmin_pro.services.secret_fields import decrypt_secret, is_encrypted_secret

        if is_encrypted_secret(raw):
            plain = decrypt_secret(raw)
            if not plain:
                logger.warning("sync_device.json decrypt failed (wrong machine?)", exc_info=False)
                return None
            data = json.loads(plain)
        else:
            data = json.loads(raw)
            mid = str(data.get("machine_id") or "").strip().upper()
            token = str(data.get("sync_token") or "").strip()
            if mid and token:
                logger.warning("sync_device.json was stored in plaintext; re-encrypting immediately")
                save_sync_credentials(mid, token)
                return (mid, token)
            return None
        mid = str(data.get("machine_id") or "").strip().upper()
        token = str(data.get("sync_token") or "").strip()
        if mid and token:
            return (mid, token)
    except (OSError, ValueError, TypeError) as exc:
        logger.warning("sync_device.json corrupt: %s", exc, exc_info=True)
        try:
            corrupt = path.with_suffix(".corrupt")
            if not corrupt.exists():
                path.rename(corrupt)
        except OSError:
            pass
    return None


def _license_code() -> str | None:
    path = find_license_file()
    if path is None:
        return None
    try:
        text = path.read_text(encoding="utf-8").strip()
        return text or None
    except OSError:
        return None
