"""Tests for SkyAgent data-first answer router."""

from __future__ import annotations

from skyadmin_pro.services.skyagent._router import MISS, answer
from skyadmin_pro.services.skyagent.llm_interface import SkyAgentLLM
from skyadmin_pro.services.skyagent.rag import RAGIndex


class FakeDB:
    def __init__(self, *, clients=None, pending=None, overdue=None):
        self._clients = clients or []
        self._pending = pending or []
        self._overdue = overdue or []
        self.client_calls = 0
        self.pending_calls = 0
        self.overdue_calls = 0

    def search_clients(self, query: str, limit: int = 20):
        self.client_calls += 1
        return list(self._clients)

    def get_pending_tasks(self, limit: int = 50):
        self.pending_calls += 1
        return list(self._pending)

    def get_overdue_documents(self):
        self.overdue_calls += 1
        return list(self._overdue)


class SpyLLM:
    def __init__(self, *, healthy=True, reply="refined"):
        self.healthy = healthy
        self.reply = reply
        self.summarize_calls: list[dict] = []

    def health_check(self) -> bool:
        return self.healthy

    def summarize(self, documents: str, *, question: str) -> str:
        self.summarize_calls.append({"documents": documents, "question": question})
        return self.reply


class DownLLM:
    def health_check(self) -> bool:
        return False

    def summarize(self, documents: str, *, question: str) -> str:
        raise RuntimeError("should not be called")


class FailingSummarizeLLM:
    def health_check(self) -> bool:
        return True

    def summarize(self, documents: str, *, question: str) -> str:
        raise ConnectionError("down")


def _rag_with(text: str, source: str = "policy.md") -> RAGIndex:
    idx = RAGIndex()
    idx.build([{"source": source, "text": text}])
    return idx


def test_db_hit_short_circuits_before_rag():
    db = FakeDB(clients=[{"id": 1, "name": "ABC Corp"}])
    rag = _rag_with("Tax filing deadline is March 31.")
    out = answer("ABC", db, rag)
    assert "ABC Corp" in out
    assert db.client_calls == 1
    assert "Tax filing" not in out


def test_db_miss_then_rag_hit():
    db = FakeDB(clients=[])
    rag = _rag_with("Refund requests within 30 days of purchase.")
    out = answer("refund policy days", db, rag)
    assert "Refund" in out or "30 days" in out
    assert "[policy.md]" in out


def test_both_miss_returns_explicit_message():
    db = FakeDB()
    rag = RAGIndex()
    assert answer("zzz nonexistent", db, rag) == MISS


def test_pending_keyword_uses_pending_tasks():
    db = FakeDB(pending=[{"id": 1, "title": "File VAT", "status": "pending"}])
    out = answer("show pending tasks", db, RAGIndex())
    assert "File VAT" in out
    assert db.pending_calls == 1
    assert db.client_calls == 0


def test_overdue_keyword_uses_overdue_docs():
    db = FakeDB(overdue=[{"id": 9, "document_type": "invoice", "client_name": "XYZ"}])
    out = answer("list overdue invoices", db, RAGIndex())
    assert "invoice" in out
    assert db.overdue_calls == 1


def test_online_refine_uses_only_local_context():
    db = FakeDB(clients=[{"name": "ABC Corp"}])
    spy = SpyLLM(reply="Polished summary of ABC")
    out = answer("ABC", db, RAGIndex(), llm=spy)
    assert out == "Polished summary of ABC"
    assert len(spy.summarize_calls) == 1
    assert "ABC Corp" in spy.summarize_calls[0]["documents"]


def test_online_down_falls_back_to_local_format():
    db = FakeDB(clients=[{"name": "ABC Corp"}])
    out = answer("ABC", db, RAGIndex(), llm=DownLLM())
    assert "ABC Corp" in out
    out2 = answer("ABC", db, RAGIndex(), llm=FailingSummarizeLLM())
    assert "ABC Corp" in out2


def test_no_data_skips_generative_llm():
    spy = SpyLLM(reply="hallucinated")
    out = answer("nothing here", FakeDB(), RAGIndex(), llm=spy)
    assert out == MISS
    assert spy.summarize_calls == []


def test_product_path_does_not_default_to_mock_chars():
    """Router without llm formats local data — never MockProvider text."""
    db = FakeDB(clients=[{"name": "Solo"}])
    out = answer("Solo", db, RAGIndex(), llm=None)
    assert "Mock Response" not in out
    assert "chars" not in out
    # MockProvider still exists for tests, but wrapping it is not product default
    mock_llm = SkyAgentLLM()
    assert "Mock" in mock_llm.draft_reply("x", context="c")
