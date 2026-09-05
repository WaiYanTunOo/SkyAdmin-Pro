"""Stress test — 500 clients × 10 services, WAL mode, concurrent reads during writes."""

from __future__ import annotations

import threading
import time

import pytest

from skyadmin_pro.config import SERVICE_TYPES
from skyadmin_pro.database import Database

NUM_CLIENTS = 500
SERVICES_PER_CLIENT = 10


@pytest.fixture
def db(tmp_path):
    return Database(tmp_path / "stress.db")


def _seed_clients(db: Database) -> list[int]:
    """Create NUM_CLIENTS clients and return their IDs."""
    ids = []
    for i in range(NUM_CLIENTS):
        cid = db.get_or_create_client(f"Client {i:04d}")
        ids.append(cid)
    return ids


def _seed_services(db: Database, client_ids: list[int]) -> int:
    """Create SERVICES_PER_CLIENT documents per client. Returns total doc count."""
    total = 0
    for cid in client_ids:
        for j in range(SERVICES_PER_CLIENT):
            doc_type = SERVICE_TYPES[j % len(SERVICE_TYPES)]
            db.record_document(
                client_id=cid,
                document_type=doc_type,
                file_name=f"doc_{j:02d}.pdf",
                file_path=f"/docs/doc_{j:02d}.pdf",
                expiry_date=f"2026-{(j % 12) + 1:02d}-{(j % 28) + 1:02d}",
            )
            total += 1
    return total


# ── Baseline seeding ──────────────────────────────────────────────────────


class TestStressSeeding:
    def test_seed_500_clients_with_services(self, db):
        client_ids = _seed_clients(db)
        assert len(client_ids) == NUM_CLIENTS

        doc_count = _seed_services(db, client_ids)
        assert doc_count == NUM_CLIENTS * SERVICES_PER_CLIENT

    def test_list_clients_performance(self, db):
        _seed_clients(db)
        start = time.perf_counter()
        clients = db.list_clients()
        elapsed = time.perf_counter() - start
        assert len(clients) == NUM_CLIENTS
        assert elapsed < 2.0, f"list_clients took {elapsed:.2f}s (> 2s)"

    def test_search_clients_performance(self, db):
        _seed_clients(db)
        start = time.perf_counter()
        results = db.search_clients("Client 0250")
        elapsed = time.perf_counter() - start
        assert len(results) >= 1
        assert elapsed < 1.0, f"search_clients took {elapsed:.2f}s (> 1s)"

    def test_list_client_services_performance(self, db):
        client_ids = _seed_clients(db)
        _seed_services(db, client_ids)
        start = time.perf_counter()
        for cid in client_ids[:50]:
            services = db.list_client_services(cid)
            assert len(services) == SERVICES_PER_CLIENT
        elapsed = time.perf_counter() - start
        assert elapsed < 2.0, f"50× list_client_services took {elapsed:.2f}s (> 2s)"


# ── WAL mode ──────────────────────────────────────────────────────────────


class TestWALMode:
    def test_wal_enabled(self, db):
        row = db._fetch_one("PRAGMA journal_mode")
        assert row is not None
        assert row["journal_mode"].lower() == "wal"

    def test_wal_survives_reopen(self, db, tmp_path):
        _seed_clients(db)
        db_path = tmp_path / "stress.db"
        db._close_pooled_conn()
        db2 = Database(db_path)
        row = db2._fetch_one("PRAGMA journal_mode")
        assert row is not None
        assert row["journal_mode"].lower() == "wal"
        clients = db2.list_clients()
        assert len(clients) == NUM_CLIENTS


# ── Concurrent reads during writes ────────────────────────────────────────


class TestConcurrentReadsWrites:
    def test_concurrent_reads_during_sequential_writes(self, db):
        """Write clients in main thread while reading threads query simultaneously."""
        write_errors: list[Exception] = []
        read_results: list[int] = []
        read_errors: list[Exception] = []
        stop_event = threading.Event()

        def reader():
            """Continuously read clients until stop_event is set."""
            while not stop_event.is_set():
                try:
                    clients = db.list_clients()
                    read_results.append(len(clients))
                except Exception as e:
                    read_errors.append(e)
                time.sleep(0.01)

        # Start reader threads
        threads = [threading.Thread(target=reader, daemon=True) for _ in range(4)]
        for t in threads:
            t.start()

        # Write clients
        try:
            for i in range(100):
                db.get_or_create_client(f"Concurrent {i:04d}")
        except Exception as e:
            write_errors.append(e)

        # Signal readers to stop and wait
        stop_event.set()
        for t in threads:
            t.join(timeout=5)

        assert not write_errors, f"Write errors: {write_errors}"
        assert not read_errors, f"Read errors: {read_errors}"
        assert len(read_results) > 0, "No reads completed"

        # Verify final state
        clients = db.list_clients()
        assert len(clients) >= 100

    def test_concurrent_reads_during_document_writes(self, db):
        """Write documents in main thread while reading threads query services."""
        cid = db.get_or_create_client("Concurrent Client")
        read_results: list[int] = []
        read_errors: list[Exception] = []
        stop_event = threading.Event()

        def reader():
            while not stop_event.is_set():
                try:
                    services = db.list_client_services(cid)
                    read_results.append(len(services))
                except Exception as e:
                    read_errors.append(e)
                time.sleep(0.01)

        threads = [threading.Thread(target=reader, daemon=True) for _ in range(3)]
        for t in threads:
            t.start()

        for i in range(50):
            db.record_document(
                client_id=cid,
                document_type=SERVICE_TYPES[i % len(SERVICE_TYPES)],
                file_name=f"doc_{i:02d}.pdf",
                file_path=f"/docs/doc_{i:02d}.pdf",
            )

        stop_event.set()
        for t in threads:
            t.join(timeout=5)

        assert not read_errors, f"Read errors: {read_errors}"
        assert len(read_results) > 0

    def test_concurrent_dashboard_queries(self, db):
        """Run dashboard_snapshot from multiple threads simultaneously."""
        client_ids = _seed_clients(db)
        _seed_services(db, client_ids[:20])
        read_errors: list[Exception] = []
        results: list[dict] = []
        stop_event = threading.Event()

        def reader():
            while not stop_event.is_set():
                try:
                    snapshot = db.dashboard_snapshot()
                    results.append(snapshot)
                except Exception as e:
                    read_errors.append(e)
                time.sleep(0.05)

        threads = [threading.Thread(target=reader, daemon=True) for _ in range(4)]
        for t in threads:
            t.start()

        time.sleep(0.5)
        stop_event.set()
        for t in threads:
            t.join(timeout=5)

        assert not read_errors, f"Read errors: {read_errors}"
        assert len(results) > 0
        for snapshot in results:
            assert "counts" in snapshot


# ── Bulk operations ───────────────────────────────────────────────────────


class TestBulkOperations:
    def test_bulk_search_performance(self, db):
        _seed_clients(db)
        start = time.perf_counter()
        for i in range(100):
            db.search_clients(f"Client {i:04d}")
        elapsed = time.perf_counter() - start
        assert elapsed < 5.0, f"100 searches took {elapsed:.2f}s (> 5s)"

    def test_bulk_task_creation(self, db):
        client_ids = _seed_clients(db)[:50]
        start = time.perf_counter()
        for cid in client_ids:
            db.add_task(title=f"Task for {cid}", client_id=cid)
        elapsed = time.perf_counter() - start
        tasks = db.list_tasks()
        assert len(tasks) >= 50
        assert elapsed < 2.0, f"50 task creations took {elapsed:.2f}s (> 2s)"

    def test_pricing_matrix_operations(self, db):
        start = time.perf_counter()
        for i in range(20):
            db.add_pricing_tier(
                service_type=f"Service {i}",
                transaction_range=f"{i * 10}-{(i + 1) * 10}",
                monthly_fee=1000 * (i + 1),
                annual_fee=10000 * (i + 1),
                sla_hours=24,
                headcount=1,
            )
        elapsed = time.perf_counter() - start
        matrix = db.get_pricing_matrix()
        assert len(matrix) >= 20
        assert elapsed < 1.0, f"20 pricing tiers took {elapsed:.2f}s (> 1s)"

    def test_supplier_operations_bulk(self, db):
        start = time.perf_counter()
        supplier_ids = []
        for i in range(30):
            sid = db.add_supplier(name=f"Supplier {i:03d}", company_name=f"SCo {i}")
            supplier_ids.append(sid)
            db.add_supplier_service(
                supplier_id=sid,
                company_name=f"Client {i}",
                service_type="VO",
            )
        elapsed = time.perf_counter() - start
        suppliers = db.list_suppliers()
        assert len(suppliers) >= 30
        assert elapsed < 2.0, f"30 supplier operations took {elapsed:.2f}s (> 2s)"
