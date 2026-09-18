from __future__ import annotations

from skyadmin_pro.services.export import FORBIDDEN_EXPORT_COLUMNS


def _cell(value: object) -> str:
    if value is None:
        return "—"
    text = str(value).strip()
    return text if text else "—"


def _project(row: dict, keys: tuple[str, ...]) -> list[str]:
    safe_keys = tuple(k for k in keys if str(k).lower() not in FORBIDDEN_EXPORT_COLUMNS)
    return [_cell(row.get(key)) for key in safe_keys]


def _assert_no_forbidden(model: dict) -> None:
    """Defense in depth: no forbidden column name may appear in keys or values."""

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if str(key).lower() in FORBIDDEN_EXPORT_COLUMNS:
                    raise ValueError(f"Refusing report — forbidden key: {key}")
                walk(value)
        elif isinstance(node, list | tuple):
            for item in node:
                walk(item)

    walk(model)
