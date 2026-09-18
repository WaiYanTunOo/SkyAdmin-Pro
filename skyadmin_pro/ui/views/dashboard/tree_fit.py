"""Shrink dashboard trees so empty lists are not 10-row blanks."""

from __future__ import annotations


def fit_tree(tree, count: int, *, empty: int = 1, cap: int = 4) -> None:
    height = empty if count <= 0 else min(cap, max(1, count))
    try:
        tree.tree.configure(height=height)
    except Exception:
        pass
