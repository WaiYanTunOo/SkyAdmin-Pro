from __future__ import annotations

from datetime import datetime

SNIPPET_PACK_FORMAT = "skyadmin-snippets"
SNIPPET_PACK_VERSION = 1


def pack_snippet_pack(active: dict, history: list[dict]) -> dict:
    """Bundle active messages + version history into a portable JSON dict."""
    return {
        "format": SNIPPET_PACK_FORMAT,
        "version": SNIPPET_PACK_VERSION,
        "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "active": active,
        "history": [
            {
                "created_at": item.get("created_at") or "",
                "note": item.get("note") or "",
                "snapshot": item.get("snapshot") or {},
            }
            for item in history
        ],
    }


def _clean_section(value) -> dict[str, dict[str, str]]:
    """Coerce one section of overrides to {label: {label, text}}, dropping junk."""
    if not isinstance(value, dict):
        return {}
    clean: dict[str, dict[str, str]] = {}
    for key, entry in value.items():
        if not isinstance(entry, dict):
            continue
        clean[str(key)] = {
            "label": str(entry.get("label") or ""),
            "text": str(entry.get("text") or ""),
        }
    return clean


def unpack_snippet_pack(data: dict) -> dict:
    """Validate an exported pack and return {'active', 'history'}."""
    if not isinstance(data, dict):
        raise ValueError("Not a messages pack.")
    if data.get("format") != SNIPPET_PACK_FORMAT:
        raise ValueError("Not a SkyAdmin messages file.")
    version = data.get("version")
    if version != SNIPPET_PACK_VERSION:
        raise ValueError(f"Unsupported messages file version: {version}.")
    active = data.get("active") or {}
    history = data.get("history") or []
    if not isinstance(active, dict) or not isinstance(history, list):
        raise ValueError("Messages file is corrupt.")
    clean_active = {section: _clean_section(section_value) for section, section_value in active.items()}
    clean_history = []
    for item in history:
        if not isinstance(item, dict):
            continue
        snapshot = item.get("snapshot")
        if not isinstance(snapshot, dict):
            continue
        clean_snapshot = {section: _clean_section(section_value) for section, section_value in snapshot.items()}
        clean_history.append(
            {
                "created_at": item.get("created_at") or "",
                "note": item.get("note") or "",
                "snapshot": clean_snapshot,
            }
        )
    return {"active": clean_active, "history": clean_history}
