"""CPU-bound work in a child process (GIL bypass for export/PDF).

Callables passed to :func:`run_in_process` must be top-level and picklable.
Database connections and Tk widgets must never cross the process boundary —
gather plain data in the parent, then offload pure computation.
"""

from __future__ import annotations

import atexit
import logging
import multiprocessing as mp
import os
import threading
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor
from typing import Any, TypeVar

_log = logging.getLogger(__name__)
_T = TypeVar("_T")

_POOL_RESULT_TIMEOUT = 300.0

_pool: ProcessPoolExecutor | None = None
_pool_lock = threading.Lock()


def _shutdown_pool() -> None:
    global _pool
    with _pool_lock:
        pool, _pool = _pool, None
    if pool is not None:
        try:
            pool.shutdown(wait=False, cancel_futures=True)
        except Exception:
            _log.debug("Process pool shutdown failed", exc_info=True)


atexit.register(_shutdown_pool)


def offload_enabled() -> bool:
    """Process offload is on by default; set SKYADMIN_PROCESS_OFFLOAD=0 to disable."""
    return os.environ.get("SKYADMIN_PROCESS_OFFLOAD", "1").strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    )


def run_in_process(fn: Callable[..., _T], *args: Any) -> _T:
    """Run a picklable top-level callable in a spawned worker process."""
    if not offload_enabled():
        return fn(*args)
    global _pool
    with _pool_lock:
        if _pool is None:
            ctx = mp.get_context("spawn")
            _pool = ProcessPoolExecutor(max_workers=1, mp_context=ctx)
            _log.debug("Started process pool for CPU offload")
        pool = _pool
    return pool.submit(fn, *args).result(timeout=_POOL_RESULT_TIMEOUT)


def _echo(value: Any) -> Any:
    """Picklable identity used by unit tests."""
    return value
