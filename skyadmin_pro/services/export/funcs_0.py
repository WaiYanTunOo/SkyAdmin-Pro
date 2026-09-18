from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from ._const_10 import FORBIDDEN_EXPORT_COLUMNS


def _assert_export_columns_safe(columns) -> None:
    bad = FORBIDDEN_EXPORT_COLUMNS.intersection(str(c).lower() for c in columns)
    if bad:
        raise ValueError(f"Refusing export — forbidden column(s): {', '.join(sorted(bad))}")


def _ordered_keys(records: list[dict[str, Any]]) -> list[str]:
    """Column-key order matching pandas' list-of-dicts DataFrame construction."""
    seen: list[str] = []
    for record in records:
        for key in record:
            if key not in seen:
                seen.append(key)
    return seen


def _sheet_rows(records: list[dict[str, Any]], mapping: dict[str, str]) -> tuple[list[str], list[list[Any]]]:
    """Return (headers, rows) for a sheet using the column mapping.

    Mirrors the old pandas path: only mapping keys present in the data are
    kept (in mapping order); empty data yields the full header set; data with
    no matching keys yields no headers and no rows.
    """
    keep = [column for column in mapping if column in _ordered_keys(records)]
    _assert_export_columns_safe(keep)
    if not records:
        return list(mapping.values()), []
    if not keep:
        return [], []
    headers = [mapping[column] for column in keep]
    rows = [[record.get(column) for column in keep] for record in records]
    return headers, rows


def _atomic_excel_write(writer_builder, dest: Path) -> Path:
    """Build the workbook at a temp path, then atomically swap into place.

    If the destination is locked (open in Excel), no partial file is left
    behind and the original error surfaces to the caller.
    """
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.stem + ".partial" + dest.suffix)
    try:
        writer_builder(tmp)
        os.replace(tmp, dest)
    except (
        OSError,
        ValueError,
        KeyError,
    ):  # defensive: openpyxl can raise any type — clean tmp, then re-raise
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return dest


def _plain_rows(rows: list[Any]) -> list[dict[str, Any]]:
    """Normalize DB rows to picklable dicts (no sqlite Row objects)."""
    out: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            out.append(dict(row))
        else:
            out.append({k: row[k] for k in row})
    return out
