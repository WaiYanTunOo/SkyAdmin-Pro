from __future__ import annotations

from ._allowed_a import PART_A
from ._allowed_b import PART_B
from ._allowed_c import PART_C
from ._allowed_d import PART_D
from ._allowed_e import PART_E

SYNC_ALLOWED_COLUMNS: dict[str, frozenset[str]] = {
    **PART_A,
    **PART_B,
    **PART_C,
    **PART_D,
    **PART_E,
}
