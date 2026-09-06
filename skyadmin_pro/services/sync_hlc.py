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

import logging
import re
import time

logger = logging.getLogger(__name__)

SETTING_SYNC_HLC_LAST = "sync_hlc_last"

_HLC_RE = re.compile(r"^(\d{1,15})-(\d{1,9})-([A-Z0-9]{1,32})$")

_node_cache: str | None = None


def node_id() -> str:
    """Stable short node id for this machine (cached per process)."""
    global _node_cache
    if _node_cache is not None:
        return _node_cache
    try:
        from skyadmin_pro.services.license.machine import get_machine_id

        raw = re.sub(r"[^A-Z0-9]", "", str(get_machine_id() or "").upper())
        _node_cache = (raw or "UNSET")[:16]
    except Exception:
        logger.warning("Machine ID unavailable for HLC node; using UNSET", exc_info=True)
        _node_cache = "UNSET"
    return _node_cache


def parse_hlc(value: object) -> tuple[int, int, str] | None:
    """Parse an HLC string to ``(wall_ms, counter, node)``; None if invalid."""
    if not value:
        return None
    match = _HLC_RE.match(str(value).strip().upper())
    if not match:
        return None
    try:
        return (int(match.group(1)), int(match.group(2)), match.group(3))
    except ValueError:
        return None


def format_hlc(wall_ms: int, counter: int, node: str) -> str:
    return f"{int(wall_ms):013d}-{int(counter):04d}-{node}"


def legacy_hlc(updated_at: str) -> tuple[int, int, str]:
    """Synthesize an HLC for unclocked rows from their ``updated_at``."""
    from skyadmin_pro.services.data_sync import _parse_updated_at

    try:
        return (int(_parse_updated_at(updated_at or "") * 1000), 0, "")
    except Exception:
        return (0, 0, "")


def hlc_now(db=None, *, node: str | None = None) -> str:
    """Stamp a new HLC, monotonic against the persisted last clock.

    When *db* is given, the clock is loaded from / persisted to the
    ``sync_hlc_last`` setting so restarts and clock skew cannot go backwards.
    """
    node = node or node_id()
    wall_ms = int(time.time() * 1000)
    last_ms, last_counter = 0, 0
    if db is not None:
        try:
            parsed = parse_hlc(db.get_setting(SETTING_SYNC_HLC_LAST))
            if parsed is not None:
                last_ms, last_counter, _ = parsed
        except Exception:
            logger.warning("Could not read last HLC", exc_info=True)
    # Same-ms or clock skew: the counter keeps the clock monotonic.
    stamped = format_hlc(wall_ms, 0, node) if wall_ms > last_ms else format_hlc(last_ms, last_counter + 1, node)
    if db is not None:
        try:
            db.set_setting(SETTING_SYNC_HLC_LAST, stamped)
        except Exception:
            logger.warning("Could not persist HLC", exc_info=True)
    return stamped


def note_remote_hlc(db, hlc_value: object) -> None:
    """Fast-forward the persisted clock past an incoming HLC (pull path)."""
    parsed = parse_hlc(hlc_value)
    if parsed is None or db is None:
        return
    try:
        current = parse_hlc(db.get_setting(SETTING_SYNC_HLC_LAST))
    except Exception:
        current = None
    if current is None or parsed > current:
        try:
            db.set_setting(SETTING_SYNC_HLC_LAST, format_hlc(*parsed))
        except Exception:
            logger.warning("Could not persist remote HLC", exc_info=True)
