"""SQL updates for portable path normalization."""

from __future__ import annotations


def update_documents(conn, doc_id: int, rel: str, *, name: str = "", clear: bool = False) -> None:
    if clear:
        conn.execute(
            "UPDATE documents SET file_path = '', file_name = '', drive_file_id = '', "
            "updated_at = datetime('now', 'localtime') WHERE id = ?",
            (doc_id,),
        )
        return
    conn.execute(
        "UPDATE documents SET file_path = ?, "
        "file_name = COALESCE(NULLIF(TRIM(file_name), ''), ?), "
        "updated_at = datetime('now', 'localtime') WHERE id = ?",
        (rel, name, doc_id),
    )


def update_financial(conn, doc_id: int, rel: str, *, name: str = "", clear: bool = False) -> None:
    if clear:
        conn.execute(
            "UPDATE financial_documents SET file_path = '', stored_path = '', file_name = '', "
            "drive_file_id = '', updated_at = datetime('now', 'localtime') WHERE id = ?",
            (doc_id,),
        )
        return
    conn.execute(
        "UPDATE financial_documents SET file_path = ?, stored_path = ?, "
        "file_name = COALESCE(NULLIF(TRIM(file_name), ''), ?), "
        "updated_at = datetime('now', 'localtime') WHERE id = ?",
        (rel, rel, name, doc_id),
    )
