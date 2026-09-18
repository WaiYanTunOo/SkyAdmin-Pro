from __future__ import annotations

import csv
from pathlib import Path

from skyadmin_pro.database import Database

from ._const_0 import logger
from ._const_1 import _REQUIRED_COLUMNS
from ._const_2 import _OPTIONAL_COLUMNS


def import_clients_from_csv(db: Database, csv_path: Path) -> dict[str, int]:
    """Import clients from a CSV file.

    Returns a summary dict with keys: imported, skipped, errors.
    Deduplicates by client name (case-insensitive).
    """
    stats = {"imported": 0, "skipped": 0, "errors": 0}
    existing_names = {name.lower() for name in db.list_client_names()}

    try:
        if csv_path.stat().st_size > 10 * 1024 * 1024:
            logger.warning("CSV too large (>10MB): %s", csv_path)
            stats["errors"] = 1
            return stats
        text = csv_path.read_text(encoding="utf-8-sig")
    except Exception as exc:
        logger.warning("Failed to read CSV: %s", exc)
        stats["errors"] = 1
        return stats

    reader = csv.DictReader(text.splitlines())
    if reader.fieldnames is None:
        stats["errors"] = 1
        return stats

    # Normalize header names
    normalized = {h.strip().lower().replace(" ", "_"): h for h in reader.fieldnames}

    # Check required columns
    if not _REQUIRED_COLUMNS.issubset(normalized.keys()):
        missing = _REQUIRED_COLUMNS - set(normalized.keys())
        logger.warning("CSV missing required columns: %s", missing)
        stats["errors"] = 1
        return stats

    rows = list(reader)
    if len(rows) > 50_000:
        logger.warning("CSV too many rows (>50000): %s", csv_path)
        stats["errors"] = 1
        return stats
    _import_clients_from_csv_p1(db, existing_names, normalized, rows, stats)

    return stats


def _import_clients_from_csv_p1(db, existing_names, normalized, rows, stats):
    # test doubles may lack the bundle helper
    ctx = db.bundle_queries() if hasattr(db, "bundle_queries") else db.connection()
    with ctx:
        for row_num, row in enumerate(rows, start=2):
            try:
                name = (row.get(normalized.get("name", "name")) or "").strip()
                if not name:
                    stats["errors"] += 1
                    continue

                # Deduplicate by name
                if name.lower() in existing_names:
                    stats["skipped"] += 1
                    continue

                # Build kwargs from available columns
                kwargs: dict[str, str] = {}
                for col_key in _OPTIONAL_COLUMNS:
                    csv_header = normalized.get(col_key)
                    if csv_header and csv_header in row:
                        value = (row[csv_header] or "").strip()
                        if value:
                            kwargs[col_key] = value

                client_id = db.get_or_create_client(name)
                if kwargs:
                    db.update_client(client_id, **kwargs)

                existing_names.add(name.lower())
                stats["imported"] += 1

            except Exception as exc:
                logger.warning("Error importing row %d: %s", row_num, exc)
                stats["errors"] += 1
