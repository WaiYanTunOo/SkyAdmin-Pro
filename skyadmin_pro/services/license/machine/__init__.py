"""Machine identity helpers for license binding."""

from __future__ import annotations

from ._const_0 import _check_debugger
from .funcs_0 import (  # noqa: F403
    _check_debugger,
    _legacy_machine_id,
    _windows_stable_id,
    platform,
    uuid,
)
from .funcs_1 import (  # noqa: F403
    HARDWARE_ID_FILENAME,
    LICENSE_FILENAME,
    Path,
    _legacy_machine_id,
    _windows_stable_id,
    get_machine_id,
)


def live_machine_id() -> str:
    """Resolve at call time so patches on machine.get_machine_id are visible."""
    from skyadmin_pro.services.license import machine as machine_mod

    return machine_mod.get_machine_id()
