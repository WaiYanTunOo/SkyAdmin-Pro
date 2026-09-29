"""Tests for SkyAgent RAG (retrieval-augmented generation)."""

from __future__ import annotations

import tempfile
from pathlib import Path

from skyadmin_pro.services.skyagent._bm25 import bm25_score, tokenize
from skyadmin_pro.services.skyagent._indexer import index_docs_folder
from skyadmin_pro.services.skyagent.rag import RAGIndex


class TestTokenize:
    def test_lowercases(self):
        assert tokenize("Hello World") == ["hello", "world"]

    def test_drops_short_tokens(self):
        assert tokenize("a bb ccc") == ["bb", "ccc"]

    def test_splits_on_non_alphanumeric(self):
        assert tokenize("hello-world,foo bar") == ["hello", "world", "foo", "bar"]

    def test_empty_string(self):
        assert tokenize("") == []


class TestBM25Score:
    def test_zero_score_when_no_match(self):
        score = bm25_score(["python"], ["java"], 5.0, {"python": 2.0})
        assert score == 0.0

    def test_positive_score_when_match(self):
        score = bm25_score(["python"], ["python", "code"], 5.0, {"python": 2.0})
        assert score > 0

    def test_higher_tf_gives_higher_score(self):
        low = bm25_score(["x"], ["x", "a", "b"], 5.0, {"x": 2.0})
        high = bm25_score(["x"], ["x", "x", "x", "a", "b"], 5.0, {"x": 2.0})
        assert high > low

    def test_idf_weighting(self):
        rare = bm25_score(["rare"], ["rare"], 5.0, {"rare": 5.0})
        common = bm25_score(["common"], ["common"], 5.0, {"common": 0.5})
        assert rare > common


class TestRAGIndex:
    def test_empty_index_returns_no_results(self):
        index = RAGIndex()
        results = index.search("anything")
        assert results == []

    def test_build_with_documents(self):
        index = RAGIndex()
        docs = [
            {"source": "doc1.md", "text": "Tax filing is due every month."},
            {"source": "doc2.md", "text": "Client onboarding requires ID verification."},
        ]
        index.build(docs)
        assert index.chunk_count == 2

    def test_search_returns_relevant_chunks(self):
        index = RAGIndex()
        docs = [
            {"source": "tax.md", "text": "Tax filing deadline is the 15th of each month."},
            {"source": "hr.md", "text": "Employee benefits include health insurance."},
        ]
        index.build(docs)
        results = index.search("tax deadline")
        assert len(results) > 0
        assert results[0]["source"] == "tax.md"

    def test_search_respects_top_k(self):
        index = RAGIndex()
        docs = [{"source": f"doc{i}.md", "text": f"Document {i} about topic {i}"} for i in range(10)]
        index.build(docs)
        results = index.search("document topic", top_k=3)
        assert len(results) <= 3

    def test_search_returns_score(self):
        index = RAGIndex()
        docs = [{"source": "test.md", "text": "Python is a programming language."}]
        index.build(docs)
        results = index.search("Python")
        assert "score" in results[0]
        assert results[0]["score"] > 0

    def test_search_empty_query_returns_no_results(self):
        index = RAGIndex()
        docs = [{"source": "test.md", "text": "Some content here."}]
        index.build(docs)
        results = index.search("")
        assert results == []

    def test_search_all_short_tokens_returns_no_results(self):
        index = RAGIndex()
        docs = [{"source": "test.md", "text": "Some content here."}]
        index.build(docs)
        results = index.search("a b c")
        assert results == []

    def test_rebuild_replaces_data(self):
        index = RAGIndex()
        docs = [
            {"source": "a.md", "text": "Alpha document"},
            {"source": "b.md", "text": "Beta document"},
            {"source": "c.md", "text": "Gamma document"},
        ]
        index.build(docs)
        assert index.chunk_count == 3
        index.build([{"source": "x.md", "text": "Only one"}])
        assert index.chunk_count == 1

    def test_save_and_load(self):
        index = RAGIndex()
        docs = [{"source": "doc.md", "text": "Test content for save and load."}]
        index.build(docs)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "index.json"
            index.save(path)

            new_index = RAGIndex()
            loaded = new_index.load(path)
            assert loaded is True
            assert new_index.chunk_count == index.chunk_count

    def test_save_load_search_parity(self):
        index = RAGIndex()
        docs = [
            {"source": "tax.md", "text": "Tax filing is due monthly."},
            {"source": "hr.md", "text": "HR handles employee benefits."},
        ]
        index.build(docs)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "index.json"
            index.save(path)

            new_index = RAGIndex()
            new_index.load(path)
            original_results = index.search("tax filing")
            loaded_results = new_index.search("tax filing")
            assert len(original_results) == len(loaded_results)
            assert original_results[0]["source"] == loaded_results[0]["source"]

    def test_load_returns_false_for_missing_file(self):
        index = RAGIndex()
        result = index.load(Path("/nonexistent/path/index.json"))
        assert result is False

    def test_load_returns_false_for_corrupt_file(self):
        index = RAGIndex()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "bad.json"
            path.write_text("not valid json {{{")
            result = index.load(path)
            assert result is False

    def test_load_returns_false_for_wrong_types(self):
        index = RAGIndex()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "wrong.json"
            path.write_text('{"chunks": "not_a_list", "idf": "bad", "avg_dl": "bad"}')
            result = index.load(path)
            assert result is False

    def test_chunking_respects_paragraphs(self):
        index = RAGIndex()
        text = "First paragraph about topic A.\n\nSecond paragraph about topic B.\n\nThird paragraph about topic C."
        docs = [{"source": "test.md", "text": text}]
        index.build(docs, chunk_size=5)
        assert index.chunk_count == 3

    def test_single_chunk_for_short_doc(self):
        index = RAGIndex()
        docs = [{"source": "short.md", "text": "Short doc."}]
        index.build(docs, chunk_size=100)
        assert index.chunk_count == 1


class TestIndexDocsFolder:
    def test_indexes_md_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            (tmpdir / "doc1.md").write_text("# Title\n\nContent about taxes.")
            (tmpdir / "doc2.md").write_text("# Other\n\nContent about HR.")
            (tmpdir / "readme.txt").write_text("Not a markdown file.")

            index = index_docs_folder(tmpdir)
            assert index.chunk_count == 2

    def test_empty_folder(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            index = index_docs_folder(Path(tmpdir))
            assert index.chunk_count == 0

    def test_nonexistent_folder(self):
        index = index_docs_folder(Path("/nonexistent/folder"))
        assert index.chunk_count == 0

    def test_partial_read_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            (tmpdir / "good.md").write_text("Good content.")
            bad_file = tmpdir / "bad.md"
            bad_file.write_text("Bad content.")
            bad_file.chmod(0o000)

            try:
                index = index_docs_folder(tmpdir)
                assert index.chunk_count >= 1
            finally:
                bad_file.chmod(0o644)
