"""Fill the incentive report and size it to the row count."""

from __future__ import annotations

from .tree_fit import fit_tree


def fill_report(view) -> None:
    year, month = view._selected_report_month()
    rows = view.app.db.list_incentive_services(year, month)
    view._report_rows = {row["id_key"]: row for row in rows}

    doc_total = sum(float(r["amount"]) for r in rows if r.get("src") == "doc" and r.get("amount"))

    tree_rows = [
        (
            str(index),
            (row.get("service_date") or "")[:10] or "—",
            row.get("client_name") or "—",
            "Document" if row.get("src") == "doc" else "Pipeline",
            row.get("service") or "—",
            row.get("amount") if row.get("amount") not in (None, "") else "—",
        )
        for index, row in enumerate(rows, start=1)
    ]
    if rows:
        tree_rows.append(("", "", "", "", "Document Total", f"{doc_total:,.2f}"))

    view.report_tree.set_rows(
        tree_rows,
        iids=[row["id_key"] for row in rows] + (["__total__"] if rows else []),
        empty_message="No fees or pipeline items for this month.",
    )
    fit_tree(view.report_tree, len(tree_rows), empty=1, cap=10)
    view._detail_scroll._on_content_configure()


def open_report_row(view, iid: str | None) -> None:
    if not iid or iid == "__empty__":
        return
    row = getattr(view, "_report_rows", {}).get(iid)
    if not row:
        return
    from .jumps import open_company, open_pipeline

    if row.get("src") == "pipe":
        open_pipeline(view.app, str(row.get("id") or ""))
    else:
        open_company(view.app, row.get("client_name") or "")


def edit_selected(view) -> None:
    iid = view.report_tree.selected_iid()
    row = getattr(view, "_report_rows", {}).get(iid) if iid else None
    if not row:
        view.workflow_feedback.error("Select a report row first.")
        return
    from .incentive_edit import open_incentive_edit

    open_incentive_edit(view, row)
