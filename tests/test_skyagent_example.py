"""Full example test of all SkyAgent capabilities."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from skyadmin_pro.services.skyagent import (
    DatabaseReadOnlyError,
    LLMProviderError,
    SkyAgentDB,
    SkyAgentLLM,
)
from skyadmin_pro.services.skyagent.rag import RAGIndex


def test_message_drafting():
    print("=" * 60)
    print("1. MESSAGE DRAFTING")
    print("=" * 60)
    llm = SkyAgentLLM()
    reply = llm.draft_reply(
        "I was charged twice for my subscription",
        context="Client: ABC Corp, Account #1234, Premium plan",
        tone="empathetic",
    )
    assert "Mock Response" in reply
    assert llm.is_available is True
    print(f"Provider: {type(llm._provider).__name__}")
    print(f"Reply: {reply}")
    print(f"Health: {llm.is_available}")
    print()


def test_entity_extraction():
    print("=" * 60)
    print("2. ENTITY EXTRACTION")
    print("=" * 60)
    llm = SkyAgentLLM()
    entities = llm.extract_entities(
        "Hi, this is John Smith, email john@abc.com. "
        "My order #5678 was delivered damaged. "
        "I am very frustrated with the quality."
    )
    assert "Mock Response" in entities
    print(f"Entities: {entities}")
    print()


def test_summarize():
    print("=" * 60)
    print("3. DOCUMENT SUMMARIZATION")
    print("=" * 60)
    llm = SkyAgentLLM()
    answer = llm.summarize(
        "Tax returns must be filed by March 31st. Late filings incur a 5% penalty per month.",
        question="What is the tax filing deadline?",
    )
    assert "Mock Response" in answer
    print("Q: What is the tax filing deadline?")
    print(f"A: {answer}")
    print()


def test_rag():
    print("=" * 60)
    print("4. RAG DOCUMENT RETRIEVAL")
    print("=" * 60)
    index = RAGIndex()
    docs = [
        {
            "source": "tax_policy.md",
            "text": "Tax returns must be filed by March 31st. Late filings incur a penalty of 5% per month.",
        },
        {
            "source": "refund_policy.md",
            "text": "Refund requests must be submitted within 30 days of purchase. Refunds are processed within 5-7 business days.",
        },
        {
            "source": "onboarding.md",
            "text": "New clients must complete KYC verification. Required documents: ID proof, address proof, tax registration certificate.",
        },
    ]
    index.build(docs)
    assert index.chunk_count == 3
    print(f"Indexed {index.chunk_count} chunks")

    results = index.search("tax filing deadline")
    assert len(results) > 0
    assert results[0]["source"] == "tax_policy.md"
    print("Query: 'tax filing deadline'")
    for r in results:
        print(f"  [{r['score']:.4f}] {r['source']}: {r['text'][:60]}...")

    # Test save/load roundtrip
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "index.json"
        index.save(path)
        new_index = RAGIndex()
        assert new_index.load(path) is True
        assert new_index.chunk_count == index.chunk_count
        loaded_results = new_index.search("tax filing deadline")
        assert loaded_results[0]["source"] == "tax_policy.md"
    print("Save/load roundtrip: OK")
    print()


def test_readonly_db():
    print("=" * 60)
    print("5. READ-ONLY DB QUERIES")
    print("=" * 60)
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE clients (id INTEGER PRIMARY KEY, name TEXT, contact_name TEXT, email TEXT, status TEXT, service_type TEXT, payment_status TEXT, tax_id TEXT, created_at TEXT, deleted_at TEXT)"
    )
    conn.execute(
        "CREATE TABLE tasks (id INTEGER PRIMARY KEY, client_id INTEGER, title TEXT, status TEXT, category TEXT, due_date TEXT, deleted_at TEXT)"
    )
    conn.execute(
        """
        CREATE TABLE pipeline_items (
            id INTEGER PRIMARY KEY, client_id INTEGER, service TEXT, step INTEGER,
            step_date TEXT, updated_at TEXT, deleted_at TEXT
        )
        """
    )
    conn.execute(
        "INSERT INTO clients VALUES (1, 'ABC Corp', 'John', 'john@abc.com', 'active', 'accounting', 'paid', 'TAX001', '2024-01-01', NULL)"
    )
    conn.execute("INSERT INTO tasks VALUES (1, 1, 'File VAT', 'pending', 'tax', '2026-10-01', NULL)")
    conn.execute("INSERT INTO pipeline_items VALUES (1, 1, 'Work Permit', 8, '2026-09-01', '2026-09-01', NULL)")
    conn.commit()

    class FakeDB:
        def read_connection(self):
            @contextmanager
            def _ctx():
                yield conn

            return _ctx()

    db = SkyAgentDB(FakeDB())

    clients = db.search_clients("ABC")
    assert len(clients) == 1
    assert clients[0]["email"] == "***REDACTED***"
    print(f"Search 'ABC': {clients[0]['name']} (email={clients[0]['email']})")

    summary = db.get_client_summary(1)
    assert summary["name"] == "ABC Corp"
    assert summary["tax_id"] == "***REDACTED***"
    assert summary["email"] == "***REDACTED***"
    print(f"Client #1: {summary['name']}, tax_id={summary['tax_id']}")

    tasks = db.get_pending_tasks()
    assert len(tasks) == 1
    assert tasks[0]["service"] == "Work Permit"
    print(f"Pending pipeline: {tasks[0]['service']} ({tasks[0].get('step_label')})")

    # Test SELECT-only enforcement
    try:
        db._safe_fetch_all("INSERT INTO clients (name) VALUES ('test')")
        raise AssertionError("Should have raised")
    except DatabaseReadOnlyError:
        print("SELECT-only enforcement: OK")

    conn.close()
    print()


def test_error_handling():
    print("=" * 60)
    print("6. ERROR HANDLING")
    print("=" * 60)

    class BadProvider:
        def query(self, prompt, *, context=None, system=None):
            raise ConnectionError("Service down")

        def health_check(self):
            return False

    bad_llm = SkyAgentLLM(BadProvider())
    assert bad_llm.is_available is False
    print(f"is_available (bad provider): {bad_llm.is_available}")

    try:
        bad_llm.draft_reply("test", context="ctx")
        raise AssertionError("Should have raised")
    except LLMProviderError as e:
        assert "LLM query failed" in str(e)
        print(f"LLMProviderError caught: {e}")

    try:
        bad_llm.extract_entities("test text")
        raise AssertionError("Should have raised")
    except LLMProviderError as e:
        assert "Entity extraction failed" in str(e)
        print(f"Entity extraction error: {e}")

    try:
        bad_llm.summarize("docs", question="q")
        raise AssertionError("Should have raised")
    except LLMProviderError as e:
        assert "Summarization failed" in str(e)
        print(f"Summarization error: {e}")
    print()


if __name__ == "__main__":
    test_message_drafting()
    test_entity_extraction()
    test_summarize()
    test_rag()
    test_readonly_db()
    test_error_handling()
    print("=" * 60)
    print("ALL EXAMPLES PASSED")
    print("=" * 60)
