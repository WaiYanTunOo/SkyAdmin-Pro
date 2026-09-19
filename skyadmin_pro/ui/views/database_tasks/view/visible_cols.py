"""Map UI tree visible columns → Excel sheet field names."""

from __future__ import annotations


def add_visible_sheet_fields(result: dict, sheet: str, tree, id_map: dict) -> None:
    if tree is None or not hasattr(tree, "get_visible_columns"):
        return
    try:
        visible = tree.get_visible_columns()
    except Exception:
        return
    fields = [id_map[c] for c in visible if c in id_map]
    if fields:
        result[sheet] = fields
