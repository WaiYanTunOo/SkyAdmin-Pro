"""Hybrid logical clocks for sync merge (Phase 2, see docs/CRDT_DESIGN.md).

Row-level last-write-wins with total order — no ties, ever:

    hlc = f"{wall_ms:013d}-{counter:04d}-{node}"

* ``wall_ms`` — wall-clock millis at stamp time.
* ``counter`` — bumps when the wall clock does not advance (or goes
  backwards), so clocks stay monotonic per database.
* ``node`` — upper-alphanumeric machine id prefix; breaks cross-device ties
  deterministically.

Legacy rows without ``hlc`` synthesize ``(updated_at_epoch_ms, 0, "")`` —
the empty node sorts below any real node, so clocked writes always win
ties against unclocked rows while preserving v1 ordering among legacy rows.

Simplification vs the design doc: HLCs are assigned at push-collect time
(``collect_local_changes``, ordered by ``updated_at`` ASC) rather than at
every DB writer. Edit order is preserved, determinism holds, and dozens of
writer call sites stay untouched.
"""

from __future__ import annotations

from ._const_0 import annotations, logger, logging  # noqa: F403
from ._const_1 import SETTING_SYNC_HLC_LAST, annotations  # noqa: F403
from ._const_2 import _HLC_RE, annotations, re  # noqa: F403
from ._const_3 import _node_cache, annotations  # noqa: F403
from .funcs import format_hlc, hlc_now, legacy_hlc, node_id, note_remote_hlc, parse_hlc
