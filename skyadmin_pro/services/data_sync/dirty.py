"""Process-wide dirty flag for debounced cloud push after local DB writes."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager

_suppress_depth = 0
_dirty = False
_handler: Callable[[], None] | None = None
_in_handler = False


def set_dirty_handler(handler: Callable[[], None] | None) -> None:
    """Register the auto-sync scheduler callback (or ``None`` on stop)."""
    global _handler
    _handler = handler


def is_dirty() -> bool:
    return _dirty


def clear_dirty() -> None:
    global _dirty
    _dirty = False


@contextmanager
def suppress_dirty() -> Iterator[None]:
    """Ignore write notifications (e.g. while applying a sync round-trip)."""
    global _suppress_depth
    _suppress_depth += 1
    try:
        yield
    finally:
        _suppress_depth -= 1


def mark_dirty() -> None:
    """Flag local changes and notify the scheduler (no-op while suppressed)."""
    global _dirty, _in_handler
    if _suppress_depth > 0:
        return
    _dirty = True
    handler = _handler
    if handler is None or _in_handler:
        return
    _in_handler = True
    try:
        handler()
    except Exception as e:
        import logging

        logging.error(f"UI Error: {e}")
    finally:
        _in_handler = False


def notify_db_write() -> None:
    """Called after a successful write-connection commit."""
    mark_dirty()
