"""Phase 2 HLC merge tests: clocks, tombstones, legacy interop, ties."""

import time

from skyadmin_pro.services import data_sync
from skyadmin_pro.services.data_sync import (
    _apply_remote_change,
    apply_remote_changes,
    collect_local_changes,
)
from skyadmin_pro.services.sync_hlc import (
    format_hlc,
    hlc_now,
    legacy_hlc,
    note_remote_hlc,
    parse_hlc,
)


def _ms(days_offset=0):
    """Realistic wall-ms base for test clocks (beats legacy synthesis)."""
    return int(time.time() * 1000) + days_offset * 86400 * 1000


def _clk(ms, counter=0, node="REMOTE"):
    return format_hlc(ms, counter, node)


def test_parse_round_trip_and_rejects():
    assert parse_hlc(format_hlc(1700000000000, 3, "ABC123")) == (1700000000000, 3, "ABC123")
    assert parse_hlc("") is None
    assert parse_hlc(None) is None
    assert parse_hlc("not-a-clock") is None
    assert parse_hlc("2026-09-06 10:00:00") is None
    assert parse_hlc("2026-09-06T10:00:00Z") is None


def test_hlc_ordering_wall_counter_node():
    assert parse_hlc("0000000000001-0000-B") > parse_hlc("0000000000001-0000-A")
    assert parse_hlc("0000000000002-0000-A") > parse_hlc("0000000000001-0009-Z")
    assert parse_hlc("0000000000001-0001-A") > parse_hlc("0000000000001-0000-Z")
    # Empty node (legacy synthesis tuple) sorts below any real node.
    assert parse_hlc("0000000000001-0000-A") > (1, 0, "")
    assert legacy_hlc("2020-01-01 00:00:00") < parse_hlc(format_hlc(int(time.time() * 1000), 0, "A"))


def test_hlc_now_monotonic_and_persisted(db):
    first = hlc_now(db)
    second = hlc_now(db)
    assert parse_hlc(second) >= parse_hlc(first)
    assert db.get_setting("sync_hlc_last") == second
    # Clock skew backwards: counter path keeps monotonicity.
    note_remote_hlc(db, "9999999999999-0000-FUTURE")
    third = hlc_now(db)
    assert parse_hlc(third) > parse_hlc("9999999999999-0000-FUTURE")


def test_legacy_hlc_synthesis_orders_by_updated_at():
    old = legacy_hlc("2020-01-01 00:00:00")
    new = legacy_hlc("2026-09-06 10:00:00")
    garbage = legacy_hlc("not-a-date")
    assert old < new
    assert garbage == (0, 0, "")
    assert garbage < old


def test_collect_stamps_proto2_monotonic(db):
    from skyadmin_pro.services.data_sync import ensure_sync_ids

    db.get_or_create_client("Beta Ltd")
    db.get_or_create_client("Acme Corp")
    ensure_sync_ids(db)
    changes = collect_local_changes(db)
    assert changes, "expected push changes"
    for change in changes:
        assert change["proto"] == 2
        assert parse_hlc(change["hlc"]) is not None
    hlcs = [parse_hlc(c["hlc"]) for c in changes]
    assert hlcs == sorted(hlcs), "collect order must match HLC order"


def _seed_client(db, name="Acme Corp"):
    from skyadmin_pro.services.data_sync import ensure_sync_ids

    client_id = db.get_or_create_client(name)
    ensure_sync_ids(db)
    row = db._fetch_one("SELECT global_id, updated_at, hlc FROM clients WHERE id = ?", (client_id,))
    assert row["global_id"], "seed must have a global_id"
    return row


def test_higher_hlc_applies_over_newer_updated_at(db):
    row = _seed_client(db)
    result = _apply_remote_change(
        db,
        {
            "table": "clients",
            "global_id": row["global_id"],
            # Older wall time but a real clock beats legacy synthesis.
            "updated_at": "2020-01-01 00:00:00",
            "hlc": _clk(_ms(1)),
            "row": {"name": "Remote Name"},
        },
    )
    assert result == "applied"
    assert db._fetch_one("SELECT name FROM clients WHERE id = 1")["name"] == "Remote Name"


def test_lower_hlc_loses_and_logs_merge_clocks(db):
    row = _seed_client(db)
    # Local gets a real clock first (collect stamps changes, not rows).
    winner = _clk(_ms(0), node="LOCAL")
    with db.connection() as conn:
        conn.execute("UPDATE clients SET hlc = ? WHERE global_id = ?", (winner, row["global_id"]))
    loser = _clk(_ms(-30), node="AAAA")
    result = _apply_remote_change(
        db,
        {
            "table": "clients",
            "global_id": row["global_id"],
            "updated_at": "2030-01-01 00:00:00",
            "hlc": loser,
            "row": {"name": "Stale Name"},
        },
    )
    assert result == "skipped"
    assert db._fetch_one("SELECT name FROM clients WHERE id = 1")["name"] == "Acme Corp"
    log = db._fetch_all("SELECT hlc_winner, hlc_loser FROM sync_conflicts")
    assert log, "expected a merge-log entry"
    assert log[0]["hlc_winner"] == winner
    assert log[0]["hlc_loser"] == loser


def test_node_tiebreak_is_deterministic(db):
    row = _seed_client(db)
    base_ms = _ms(0)
    with db.connection() as conn:
        conn.execute(
            "UPDATE clients SET hlc = ? WHERE global_id = ?",
            (format_hlc(base_ms, 0, "AAAA"), row["global_id"]),
        )
    # Same wall+counter, higher node wins.
    winner = format_hlc(base_ms, 0, "ZZZZ")
    assert (
        _apply_remote_change(
            db,
            {
                "table": "clients",
                "global_id": row["global_id"],
                "updated_at": "2026-09-06 10:00:00",
                "hlc": winner,
                "row": {"name": "Winner"},
            },
        )
        == "applied"
    )
    # Exact same clock loses (<= comparison).
    assert (
        _apply_remote_change(
            db,
            {
                "table": "clients",
                "global_id": row["global_id"],
                "updated_at": "2026-09-06 10:00:00",
                "hlc": winner,
                "row": {"name": "Replay"},
            },
        )
        == "skipped"
    )


def test_tombstone_higher_hlc_deletes(db):
    row = _seed_client(db)
    result = _apply_remote_change(
        db,
        {
            "table": "clients",
            "global_id": row["global_id"],
            "updated_at": "2026-09-06 10:00:00",
            "deleted_at": "2026-09-06 10:00:00",
            "hlc": _clk(_ms(1)),
        },
    )
    assert result == "applied"
    assert db._fetch_one("SELECT deleted_at FROM clients WHERE id = 1")["deleted_at"]


def test_tombstone_lower_hlc_loses_to_live_edit(db):
    row = _seed_client(db)
    with db.connection() as conn:
        conn.execute("UPDATE clients SET hlc = ? WHERE global_id = ?", (_clk(_ms(0), node="LOCAL"), row["global_id"]))
    result = _apply_remote_change(
        db,
        {
            "table": "clients",
            "global_id": row["global_id"],
            "updated_at": "2020-01-01 00:00:00",
            "deleted_at": "2020-01-01 00:00:00",
            "hlc": _clk(_ms(-30), node="AAAA"),
        },
    )
    assert result == "skipped"
    assert not db._fetch_one("SELECT deleted_at FROM clients WHERE id = 1")["deleted_at"]


def test_v1_change_without_hlc_uses_legacy_path(db):
    row = _seed_client(db)
    assert (
        _apply_remote_change(
            db,
            {
                "table": "clients",
                "global_id": row["global_id"],
                "updated_at": "2030-01-01 00:00:00",
                "row": {"name": "V1 Name"},
            },
        )
        == "applied"
    )
    assert db._fetch_one("SELECT name FROM clients WHERE id = 1")["name"] == "V1 Name"


def test_apply_page_fast_forwards_clock(db):
    row = _seed_client(db)
    incoming = _clk(_ms(2))
    applied, _ = apply_remote_changes(
        db,
        [
            {
                "table": "clients",
                "global_id": row["global_id"],
                "updated_at": "2026-09-06 10:00:00",
                "hlc": incoming,
                "row": {"name": "Paged"},
            }
        ],
    )
    assert applied == 1
    assert parse_hlc(db.get_setting("sync_hlc_last")) >= parse_hlc(incoming)


def test_data_sync_module_exports():
    assert "SYNC_SCHEMA_VERSION" in data_sync.__all__
    from skyadmin_pro.services.sync_schema import SYNC_SCHEMA_VERSION

    assert SYNC_SCHEMA_VERSION == 3
