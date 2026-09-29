"""Tests for simple SkyAgent answer formatting."""

from __future__ import annotations

from skyadmin_pro.services.skyagent._format import filter_rows_by_query, format_rows


def test_format_pipeline_is_short():
    out = format_rows(
        [
            {
                "client_name": "SECURE NETWORKS",
                "service": "Work Permit",
                "step": 8,
                "step_label": "8. Processing & follow-up",
            },
            {
                "client_name": "SECURE NETWORKS",
                "service": "Visa",
                "step": 4,
                "step_label": "4. Requirements checked with supplier",
            },
        ]
    )
    assert out.startswith("2 service pipeline:")
    assert "• SECURE NETWORKS — Work Permit — 8. Processing & follow-up" in out
    assert "id:" not in out
    assert "status:" not in out


def test_format_caps_long_lists():
    rows = [
        {
            "client_name": "C",
            "service": f"S{i}",
            "step": 1,
            "step_label": "1. Client appoints service",
        }
        for i in range(20)
    ]
    out = format_rows(rows)
    assert "20 service pipeline" in out
    assert "… and 8 more" in out


def test_filter_requires_all_tokens():
    rows = [
        {"client_name": "SECURE NETWORKS CO", "service": "Visa", "step_label": "8. Processing"},
        {"client_name": "OTHER", "service": "X", "step_label": "1. Client"},
    ]
    kept = filter_rows_by_query(rows, "pending secure networks", drop_words={"pending"})
    assert len(kept) == 1
    assert kept[0]["service"] == "Visa"
