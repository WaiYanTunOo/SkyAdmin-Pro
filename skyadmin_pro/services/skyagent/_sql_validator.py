"""SQL validation helpers for SkyAgent read-only DB."""

from __future__ import annotations

import re

from .exceptions import DatabaseReadOnlyError

_FORBIDDEN = frozenset(
    {
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "ATTACH",
        "PRAGMA",
        "INTO",
        "ALTER",
        "CREATE",
        "REPLACE",
        "VACUUM",
        "REINDEX",
        "TRIGGER",
        "DETACH",
        "GRANT",
        "REVOKE",
    }
)
_WORD = re.compile(r"[A-Za-z_]+")
_QUOTED = re.compile(r"('([^']|'')*')|(\"([^\"]|\"\")*\")")


def _strip_quotes(sql: str) -> str:
    return _QUOTED.sub(" ", sql)


def validate_select_only(sql: str) -> None:
    """Raise DatabaseReadOnlyError unless sql is a single safe SELECT."""
    stripped = sql.strip()
    if not stripped.upper().startswith("SELECT"):
        raise DatabaseReadOnlyError("Only SELECT queries are allowed")
    for match in _WORD.finditer(_strip_quotes(stripped)):
        token = match.group(0).upper()
        if token in _FORBIDDEN:
            raise DatabaseReadOnlyError(f"Forbidden SQL keyword: {token}")


def validate_no_multiple_statements(sql: str) -> None:
    """Raise ValueError if sql contains semicolons outside of quotes."""
    in_quote = False
    quote_char = None
    for char in sql:
        if char in ("'", '"') and not in_quote:
            in_quote = True
            quote_char = char
        elif char == quote_char and in_quote:
            in_quote = False
            quote_char = None
        elif char == ";" and not in_quote:
            raise ValueError("Multiple statements not allowed")
