#!/usr/bin/env python3
"""Repair Wave D7 bogus package re-exports in skyadmin_pro/**/__init__.py.

Walks package __init__ files, AST-parses relative ``from .mod import name`` lists,
drops names that are not defined/imported at module level in the target file,
and drops known-stdlib / non-public noise when they are not real exports.

Does not mass-shred source modules — only rewrites import lists in __init__.py.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "skyadmin_pro"

# Names that shredders often re-export incorrectly (stdlib / typing glue).
ALWAYS_DROP = frozenset(
    {
        "annotations",
        "tempfile",
        "os",
        "sys",
        "json",
        "re",
        "time",
        "random",
        "logging",
        "hashlib",
        "base64",
        "zipfile",
        "sqlite3",
        "getpass",
        "urllib",
        "datetime",
        "Path",
        "Any",
        "TYPE_CHECKING",
        "__all__",
    }
)


def _collect_bound_names(nodes: list[ast.stmt], names: set[str]) -> None:
    """Collect names bound by statements, including try/if/with bodies."""
    for node in nodes:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
                elif isinstance(target, (ast.Tuple, ast.List)):
                    for elt in target.elts:
                        if isinstance(elt, ast.Name):
                            names.add(elt.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if alias.name == "*":
                    continue
                names.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.Try):
            _collect_bound_names(node.body, names)
            for handler in node.handlers:
                _collect_bound_names(handler.body, names)
            _collect_bound_names(node.orelse, names)
            _collect_bound_names(node.finalbody, names)
        elif isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor)):
            _collect_bound_names(node.body, names)
            _collect_bound_names(node.orelse, names)
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            _collect_bound_names(node.body, names)


def module_level_names(path: Path) -> set[str]:
    """Names bound at module level (defs, assigns, imports, try/if bodies)."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return set()
    names: set[str] = set()
    _collect_bound_names(tree.body, names)
    return names


def resolve_relative(init_path: Path, module: str | None, level: int) -> Path | None:
    """Map ImportFrom(module, level) to a .py path under the package."""
    if level < 1:
        return None
    base = init_path.parent
    for _ in range(level - 1):
        base = base.parent
    if module:
        parts = module.split(".")
        candidate = base.joinpath(*parts)
    else:
        candidate = base
    if candidate.with_suffix(".py").is_file():
        return candidate.with_suffix(".py")
    if (candidate / "__init__.py").is_file():
        return candidate / "__init__.py"
    return None


def filter_import_names(target: Path | None, names: list[str], *, drop_stdlib: bool) -> list[str]:
    if target is None:
        return names
    available = module_level_names(target)
    kept: list[str] = []
    for name in names:
        if drop_stdlib and name in ALWAYS_DROP:
            # Keep if genuinely defined as a product symbol (rare).
            if name not in available or name in {
                "annotations",
                "tempfile",
                "os",
                "sys",
                "json",
                "re",
                "time",
                "random",
                "logging",
                "hashlib",
                "base64",
                "zipfile",
                "sqlite3",
                "getpass",
                "urllib",
                "datetime",
                "TYPE_CHECKING",
                "__all__",
            }:
                # Drop pure stdlib re-exports even if import binds the name.
                if (
                    name in ALWAYS_DROP
                    and name
                    not in {
                        # Product symbols that share a stdlib-looking name — none today.
                    }
                ):
                    # If the target only has it via `import X`, drop; if assigned locally, keep.
                    src = target.read_text(encoding="utf-8")
                    tree = ast.parse(src)
                    is_local_assign = False
                    for node in tree.body:
                        if isinstance(node, ast.Assign):
                            for t in node.targets:
                                if isinstance(t, ast.Name) and t.id == name:
                                    is_local_assign = True
                        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                            if node.target.id == name:
                                is_local_assign = True
                        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                            if node.name == name:
                                is_local_assign = True
                    if not is_local_assign:
                        continue
        if name not in available:
            continue
        kept.append(name)
    return kept


def rewrite_init(path: Path, *, dry_run: bool = False) -> list[str]:
    """Rewrite one __init__.py; return list of change descriptions."""
    src = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(src)
    except SyntaxError as exc:
        return [f"SKIP syntax error: {exc}"]

    lines = src.splitlines(keepends=True)
    changes: list[str] = []
    # Process ImportFrom nodes bottom-up so offsets stay valid.
    imports = [n for n in tree.body if isinstance(n, ast.ImportFrom) and n.level >= 1]
    for node in reversed(imports):
        if not node.names or any(a.name == "*" for a in node.names):
            continue
        target = resolve_relative(path, node.module, node.level)
        old_names = [a.name for a in node.names]
        new_names = filter_import_names(target, old_names, drop_stdlib=True)
        if new_names == old_names:
            continue
        # Rebuild the import statement text.
        start = node.lineno - 1
        end = (node.end_lineno or node.lineno) - 1
        indent = lines[start][: len(lines[start]) - len(lines[start].lstrip())]
        mod = ("." * node.level) + (node.module or "")
        if not new_names:
            # Remove entire import.
            del lines[start : end + 1]
            changes.append(f"removed empty import from {mod}")
            continue
        if len(new_names) == 1 and start == end:
            new_stmt = f"{indent}from {mod} import {new_names[0]}\n"
        else:
            inner = ",\n".join(f"{indent}    {n}" for n in new_names)
            new_stmt = f"{indent}from {mod} import (  # noqa: F403\n{inner},\n{indent})\n"
        lines[start : end + 1] = [new_stmt]
        dropped = [n for n in old_names if n not in new_names]
        changes.append(f"{mod}: dropped {dropped}")

    if changes and not dry_run:
        path.write_text("".join(lines), encoding="utf-8")
    return changes


def main() -> int:
    dry = "--dry-run" in sys.argv
    inits = sorted(PKG.rglob("__init__.py"))
    total = 0
    for init in inits:
        rel = init.relative_to(ROOT)
        changes = rewrite_init(init, dry_run=dry)
        if changes:
            total += 1
            print(f"{'[dry] ' if dry else ''}{rel}:")
            for c in changes:
                print(f"  - {c}")
    print(f"{'Would touch' if dry else 'Touched'} {total} __init__.py file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
