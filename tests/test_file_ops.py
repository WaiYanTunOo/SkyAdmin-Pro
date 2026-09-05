"""Tests for file_ops utilities — sanitize, parse, format, build filenames."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from skyadmin_pro.services.file_ops import (
    build_invoice_filename,
    build_smart_filename,
    compact_date,
    format_thousands,
    parse_flexible_date,
    sanitize_amount,
    sanitize_token,
    unique_path,
)


class TestSanitizeToken:
    def test_basic(self):
        assert sanitize_token("Hello World") == "HelloWorld"

    def test_special_chars(self):
        result = sanitize_token('File: "Name" <test>')
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result
        assert '"' not in result

    def test_whitespace(self):
        assert sanitize_token("  a  b  ") == "ab"

    def test_empty(self):
        assert sanitize_token("") == "Unknown"

    def test_dots_stripped(self):
        assert sanitize_token("...") == "Unknown"


class TestSanitizeAmount:
    def test_basic(self):
        assert sanitize_amount("1,234.56") == "1234.56"

    def test_currency(self):
        assert sanitize_amount("THB 1,000") == "1000"

    def test_empty(self):
        result = sanitize_amount("")
        assert result == "Unknown"


class TestFormatThousands:
    def test_basic(self):
        assert format_thousands("1234567") == "1,234,567"

    def test_with_decimal(self):
        assert format_thousands("1234.56") == "1,234.56"

    def test_empty(self):
        assert format_thousands("") == ""

    def test_non_numeric(self):
        assert format_thousands("abc") == "abc"


class TestParseFlexibleDate:
    def test_iso(self):
        assert parse_flexible_date("2026-01-15") == "2026-01-15"

    def test_slash_format(self):
        assert parse_flexible_date("15/01/2026") == "2026-01-15"

    def test_dash_format(self):
        assert parse_flexible_date("15-01-2026") == "2026-01-15"

    def test_compact(self):
        assert parse_flexible_date("20260115") == "2026-01-15"

    def test_empty(self):
        assert parse_flexible_date("") is None

    def test_invalid(self):
        assert parse_flexible_date("not-a-date") is None


class TestCompactDate:
    def test_basic(self):
        assert compact_date("2026-01-15") == "20260115"


class TestBuildSmartFilename:
    def test_basic(self):
        name = build_smart_filename(
            client_name="Acme Corp",
            document_type="Passport",
            suffix=".pdf",
            today=date(2026, 1, 15),
        )
        assert name.startswith("20260115_")
        assert name.endswith(".pdf")
        assert "AcmeCorp" in name
        assert "Passport" in name

    def test_with_expiry(self):
        name = build_smart_filename(
            client_name="Test",
            document_type="Visa",
            suffix=".pdf",
            expiry_iso="2027-06-30",
            today=date(2026, 1, 15),
        )
        assert "20270630" in name

    def test_with_amount(self):
        name = build_smart_filename(
            client_name="Test",
            document_type="Invoice",
            suffix=".xlsx",
            amount="1,500",
            today=date(2026, 1, 15),
        )
        assert "1500" in name


class TestBuildInvoiceFilename:
    def test_basic(self):
        name = build_invoice_filename(
            client_name="Acme Corp",
            suffix=".pdf",
            today=date(2026, 1, 15),
        )
        assert name.startswith("202601_")
        assert "Invoice" in name
        assert name.endswith(".pdf")

    def test_with_invoice_no(self):
        name = build_invoice_filename(
            client_name="Test",
            suffix=".pdf",
            invoice_no="INV20260101",
            today=date(2026, 1, 15),
        )
        assert "INV20260101" in name


class TestUniquePath:
    def test_unique(self, tmp_path: Path):
        p = tmp_path / "test.txt"
        assert unique_path(p) == p

    def test_collision(self, tmp_path: Path):
        p = tmp_path / "test.txt"
        p.write_text("hello")
        result = unique_path(p)
        assert result != p
        assert not result.exists()  # unique_path returns a non-existing path
