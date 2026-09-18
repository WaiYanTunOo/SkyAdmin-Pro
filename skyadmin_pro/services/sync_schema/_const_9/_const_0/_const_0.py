from __future__ import annotations

from ._allowed_a import PART_A
from ._allowed_b import PART_B

SYNC_ALLOWED_COLUMNS: dict[str, frozenset[str]] = {**PART_A, **PART_B}
