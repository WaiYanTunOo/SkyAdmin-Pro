from __future__ import annotations


class GlobalSearchDialogMixin2:
    def _search_all(self, query: str, filter_type: str) -> list[dict]:
        from skyadmin_pro.services.magic_search import magic_search

        return magic_search(self.app.db, query, kind=filter_type)
