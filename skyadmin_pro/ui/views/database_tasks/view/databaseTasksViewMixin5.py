from __future__ import annotations


class DatabaseTasksViewMixin5:
    def _DatabaseTasksView_visible_sheet_columns_p3(
        self, fields, id_map, result, sheet, suppliers, tree, tree_attr, visible
    ):
        if suppliers is not None:
            for tab_attr, tree_attr, sheet, id_map in (
                (
                    "directory",
                    "supplier_tree",
                    "Suppliers",
                    {"name": "name", "company": "company_name", "contact": "contact", "notes": "notes"},
                ),
                (
                    "payments",
                    "pay_tree",
                    "Supplier Payments",
                    {
                        "supplier": "supplier_name",
                        "client": "client_name",
                        "amount": "amount",
                        "due": "due_date",
                        "paid": "paid",
                        "paid_date": "paid_date",
                        "notes": "notes",
                    },
                ),
                (
                    "services",
                    "supplier_svc_tree",
                    "Supplier Services",
                    {"company": "company_name", "service": "service_type", "expiry": "expiry_date", "notes": "notes"},
                ),
            ):
                tab = getattr(suppliers, tab_attr, None)
                tree = getattr(tab, tree_attr, None) if tab is not None else None
                if tree is None or not hasattr(tree, "get_visible_columns"):
                    continue
                try:
                    visible = tree.get_visible_columns()
                except Exception:
                    continue
                fields = [id_map[c] for c in visible if c in id_map]
                if sheet == "Supplier Services" and fields and "supplier_name" not in fields:
                    # Tree is single-supplier context (no supplier column shown),
                    # but the sheet needs attribution — data always carries it.
                    fields = ["supplier_name", *fields]
                if fields:
                    result[sheet] = fields
