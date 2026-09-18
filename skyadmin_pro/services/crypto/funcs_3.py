from __future__ import annotations

from pathlib import Path

from ._const_0 import logger
from ._const_1 import MAGIC
from .funcs_2 import _derive_fernet_key, is_encrypted


def encrypt_file(path: Path, machine_id: str) -> bool:
    """Encrypt *path* in place (prepends :data:`MAGIC`). Returns True on success."""
    if is_encrypted(path):
        return True
    try:
        import os
        import tempfile

        from cryptography.fernet import Fernet

        fernet = Fernet(_derive_fernet_key(machine_id, 200_000))
        data = path.read_bytes()
        encrypted = MAGIC + fernet.encrypt(data)
        path = Path(path)
        tmp_fd, tmp_name = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".encrypting",
        )
        try:
            with os.fdopen(tmp_fd, "wb") as handle:
                handle.write(encrypted)
            os.replace(tmp_name, path)
        except OSError:
            try:
                os.unlink(tmp_name)
            except OSError:
                logger.debug("Failed to unlink temp file %s", tmp_name, exc_info=True)
            raise
        return True
    except OSError as exc:
        logger.warning("encrypt_file failed for %s: %s", path, exc)
        return False
    except (ValueError, TypeError):
        logger.exception("encrypt_file failed for %s", path)
        return False


def decrypt_file(path: Path, machine_id: str) -> bool:
    """Decrypt *path* in place when encrypted. Returns True if decrypted."""
    if not is_encrypted(path):
        return False
    try:
        import os
        import tempfile

        from cryptography.fernet import Fernet, InvalidToken

        blob = path.read_bytes()[len(MAGIC) :]
        # Try current then legacy KDF
        for iters in (200_000, 100_000):
            try:
                fernet = Fernet(_derive_fernet_key(machine_id, iters))
                data = fernet.decrypt(blob)
                break
            except InvalidToken:
                if iters == 100_000:
                    raise
                continue
        else:
            return False
        path = Path(path)
        tmp_fd, tmp_name = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".decrypting",
        )
        try:
            with os.fdopen(tmp_fd, "wb") as handle:
                handle.write(data)
            os.replace(tmp_name, path)
        except OSError:
            try:
                os.unlink(tmp_name)
            except OSError:
                logger.debug("Failed to unlink temp file %s", tmp_name, exc_info=True)
            raise
        return True
    except (InvalidToken, OSError, ValueError):
        logger.exception("decrypt_file failed for %s", path)
        return False
