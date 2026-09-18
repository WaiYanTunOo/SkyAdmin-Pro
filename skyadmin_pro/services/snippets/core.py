from __future__ import annotations

import json

from skyadmin_pro.config import SETTING_SNIPPET_OVERRIDES

from .checklists_1 import CHECKLISTS_1
from .checklists_2 import CHECKLISTS_2
from .checklists_3 import CHECKLISTS_3
from .client_replies_1 import CLIENT_REPLIES_1
from .client_replies_2 import CLIENT_REPLIES_2
from .service_replies import SERVICE_REPLIES
from .supplier_replies import SUPPLIER_REPLIES
from .types import Snippet

CLIENT_REPLIES = CLIENT_REPLIES_1 + CLIENT_REPLIES_2
CHECKLISTS = CHECKLISTS_1 + CHECKLISTS_2 + CHECKLISTS_3
REPLIES = CLIENT_REPLIES

SNIPPET_SECTIONS: dict[str, tuple[Snippet, ...]] = {
    "client": CLIENT_REPLIES,
    "supplier": SUPPLIER_REPLIES,
    "checklist": CHECKLISTS,
    "service": SERVICE_REPLIES,
}


def apply_snippet_overrides(section: str, overrides: dict[str, dict[str, str]] | None) -> tuple[Snippet, ...]:
    """Merge saved overrides over the built-in defaults for one section.

    Overrides are keyed by the snippet's original label::
        {"Need clear photo": {"label": "Clear photo", "text": "..."}}

    Keys that do not match any built-in snippet are user-added messages; they
    are appended (sorted by label) at the end of the section.
    """
    defaults = SNIPPET_SECTIONS.get(section, ())
    if not overrides:
        return defaults
    default_labels = {snippet.label for snippet in defaults}
    merged = []
    for snippet in defaults:
        override = overrides.get(snippet.label)
        if override:
            merged.append(
                Snippet(
                    label=(override.get("label") or snippet.label).strip() or snippet.label,
                    text=(override.get("text") or snippet.text).strip() or snippet.text,
                )
            )
        else:
            merged.append(snippet)
    extras = []
    for key, value in overrides.items():
        if key in default_labels:
            continue
        label = (value.get("label") or key).strip() or key
        text = (value.get("text") or "").strip()
        if text:
            extras.append(Snippet(label=label, text=text))
    extras.sort(key=lambda snippet: snippet.label.lower())
    return tuple([*merged, *extras])


def effective_text(section: str, label: str, overrides: dict[str, dict[str, dict[str, str]]] | None = None) -> str:
    """Return the effective (override-aware) text for one snippet, or ''."""
    items = apply_snippet_overrides(section, (overrides or {}).get(section) or {})
    for snippet in items:
        if snippet.label == label:
            return snippet.text
    return ""


def load_snippet_overrides(get_setting) -> dict:
    """Safely read + parse the snippet-overrides setting.

    `get_setting` is a callable (e.g. ``db.get_setting``). Corrupt or
    non-dict JSON never raises — it degrades to no overrides.
    """
    raw = ""
    try:
        raw = get_setting(SETTING_SNIPPET_OVERRIDES) or ""
        parsed = json.loads(raw) if raw else {}
    except (ValueError, TypeError):
        return {}
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}
