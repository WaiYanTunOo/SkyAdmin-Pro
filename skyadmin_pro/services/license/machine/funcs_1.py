from __future__ import annotations

from pathlib import Path

from skyadmin_pro.services.license._constants import HARDWARE_ID_FILENAME, LICENSE_FILENAME

from .funcs_0 import _legacy_machine_id, _windows_stable_id


def get_machine_id() -> str:
    """Stable hardware-bound ID.

    Frozen once into ~/.skyadmin_pro/hardware.id (with a shadow copy in
    backups\\) so network-adapter changes or accidental deletions can never
    invalidate an activated license. New installs use the Windows
    MachineGuid; machines that already had a license under the legacy MAC
    formula keep that ID for continuity.
    """
    try:
        from skyadmin_pro.paths import app_data_dir

        base = app_data_dir()
        id_file = base / HARDWARE_ID_FILENAME
        if id_file.exists():
            stored = id_file.read_text(encoding="utf-8").strip().upper()
            if len(stored) == 16:
                return stored
        shadow = base / "backups" / (HARDWARE_ID_FILENAME + ".shadow")
        if shadow.exists():
            stored = shadow.read_text(encoding="utf-8").strip().upper()
            if len(stored) == 16:
                id_file.write_text(stored, encoding="utf-8")
                return stored
    except (OSError, ValueError):
        id_file = None
        shadow = None

    has_existing_license = False
    try:
        from skyadmin_pro.paths import app_data_dir

        has_existing_license = (Path(app_data_dir()) / LICENSE_FILENAME).exists()
    except (ImportError, OSError):
        pass

    computed = _legacy_machine_id() if has_existing_license else (_windows_stable_id() or _legacy_machine_id())
    try:
        import os
        import tempfile

        from skyadmin_pro.paths import app_data_dir

        base = Path(app_data_dir())
        # Atomic freeze: concurrent first-starts must not interleave partial writes.
        fd, tmp_name = tempfile.mkstemp(dir=str(base), prefix=".hardware_", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(computed)
            os.replace(tmp_name, base / HARDWARE_ID_FILENAME)
        finally:
            try:
                Path(tmp_name).unlink(missing_ok=True)
            except OSError:
                pass
        shadow = base / "backups" / (HARDWARE_ID_FILENAME + ".shadow")
        shadow.parent.mkdir(parents=True, exist_ok=True)
        shadow.write_text(computed, encoding="utf-8")
    except (OSError, ImportError):
        pass
    return computed
