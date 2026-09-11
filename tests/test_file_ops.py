"""Tests for file operations utilities."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from skyadmin_pro.services.file_ops import (
    build_invoice_filename,
    build_smart_filename,
    compact_date,
    copy_file,
    file_signature,
    format_thousands,
    is_image,
    is_pdf,
    list_files,
    list_files_with_signature,
    month_archive_folder,
    move_file,
    open_in_file_manager,
    parse_flexible_date,
    sanitize_amount,
    sanitize_token,
    unique_path,
)


class TestSanitizeToken:
    def test_basic(self):
        assert sanitize_token("Hello World") == "HelloWorld"

    def test_special_chars_replaced(self):
        result = sanitize_token("bad/filename\\with:special*chars.pdf")
        assert "/" not in result
        assert "\\" not in result
        assert ":" not in result
        assert "*" not in result
        assert '"' not in result
        assert "<" not in result
        assert ">" not in result
        assert "|" not in result
        assert "?" not in result

    def test_whitespace_stripped(self):
        assert sanitize_token("  a  b  ") == "ab"

    def test_empty_returns_unknown(self):
        assert sanitize_token("") == "Unknown"

    def test_only_dots_and_dashes_stripped(self):
        assert sanitize_token("...") == "Unknown"
        assert sanitize_token("---") == "Unknown"
        assert sanitize_token("._-") == "Unknown"

    def test_realistic_filename(self):
        result = sanitize_token("My File (1).pdf")
        assert result == "MyFile(1).pdf"


class TestSanitizeAmount:
    def test_basic(self):
        assert sanitize_amount("1,234.56") == "1234.56"

    def test_currency(self):
        assert sanitize_amount("THB 1,000") == "1000"

    def test_empty_falls_back(self):
        result = sanitize_amount("")
        assert result == "Unknown"

    def test_non_numeric_falls_back(self):
        result = sanitize_amount("nope")
        assert result == "nope"


class TestFormatThousands:
    def test_basic(self):
        assert format_thousands("1234567") == "1,234,567"

    def test_with_decimal(self):
        assert format_thousands("1234.56") == "1,234.56"

    def test_empty(self):
        assert format_thousands("") == ""

    def test_non_numeric(self):
        assert format_thousands("abc") == "abc"

    def test_already_formatted(self):
        assert format_thousands("1,234") == "1,234"

    def test_zero(self):
        assert format_thousands("0") == "0"

    def test_large_number(self):
        assert format_thousands("1234567890") == "1,234,567,890"


class TestParseFlexibleDate:
    def test_iso(self):
        assert parse_flexible_date("2026-01-15") == "2026-01-15"

    def test_slash_format(self):
        assert parse_flexible_date("15/01/2026") == "2026-01-15"

    def test_dash_format(self):
        assert parse_flexible_date("15-01-2026") == "2026-01-15"

    def test_compact(self):
        assert parse_flexible_date("20260115") == "2026-01-15"

    def test_dot_format(self):
        assert parse_flexible_date("15.01.2026") == "2026-01-15"

    def test_empty(self):
        assert parse_flexible_date("") is None

    def test_whitespace_only(self):
        assert parse_flexible_date("   ") is None

    def test_invalid(self):
        assert parse_flexible_date("not-a-date") is None


class TestCompactDate:
    def test_basic(self):
        assert compact_date("2026-01-15") == "20260115"

    def test_already_compact(self):
        assert compact_date("20260115") == "20260115"


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

    def test_suffix_without_dot(self):
        name = build_smart_filename(
            client_name="Test",
            document_type="Invoice",
            suffix="pdf",
            today=date(2026, 1, 15),
        )
        assert name.endswith(".pdf")


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

    def test_invoice_no_auto_prefix(self):
        name = build_invoice_filename(
            client_name="Test",
            suffix=".pdf",
            invoice_no="20260101",
            today=date(2026, 1, 15),
        )
        assert "INV20260101" in name

    def test_empty_invoice_no(self):
        name = build_invoice_filename(
            client_name="Test",
            suffix=".pdf",
            invoice_no="",
            today=date(2026, 1, 15),
        )
        assert "INV" in name


class TestUniquePath:
    def test_unique(self, tmp_path: Path):
        p = tmp_path / "test.txt"
        assert unique_path(p) == p

    def test_collision(self, tmp_path: Path):
        p = tmp_path / "test.txt"
        p.write_text("hello")
        result = unique_path(p)
        assert result != p
        assert not result.exists()

    def test_multiple_collisions(self, tmp_path: Path):
        p = tmp_path / "test.txt"
        p.write_text("a")
        (tmp_path / "test_2.txt").write_text("b")
        (tmp_path / "test_3.txt").write_text("c")
        result = unique_path(p)
        assert result.name == "test_4.txt"


class TestListFiles:
    def test_returns_sorted(self, tmp_path: Path):
        (tmp_path / "b.txt").write_text("b")
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "c.txt").write_text("c")
        result = list_files(tmp_path)
        assert [p.name for p in result] == ["a.txt", "b.txt", "c.txt"]

    def test_excludes_hidden(self, tmp_path: Path):
        (tmp_path / "visible.txt").write_text("v")
        (tmp_path / ".hidden").write_text("h")
        result = list_files(tmp_path)
        assert len(result) == 1
        assert result[0].name == "visible.txt"

    def test_nonexistent_folder(self, tmp_path: Path):
        result = list_files(tmp_path / "nope")
        assert result == []


class TestListFilesWithSignature:
    def test_returns_files_and_signature(self, tmp_path: Path):
        (tmp_path / "a.txt").write_text("hello")
        files, sig = list_files_with_signature(tmp_path)
        assert len(files) == 1
        assert len(sig) == 1
        assert sig[0][0] == "a.txt"


class TestFileSignature:
    def test_returns_tuple(self, tmp_path: Path):
        (tmp_path / "a.txt").write_text("hello")
        sig = file_signature(tmp_path)
        assert isinstance(sig, tuple)
        assert len(sig) == 1


class TestMoveFile:
    def test_moves_file(self, tmp_path: Path):
        src = tmp_path / "source.txt"
        src.write_text("content")
        dest_dir = tmp_path / "dest"
        result = move_file(src, dest_dir)
        assert result.exists()
        assert not src.exists()
        assert result.parent == dest_dir

    def test_moves_with_new_name(self, tmp_path: Path):
        src = tmp_path / "source.txt"
        src.write_text("content")
        dest_dir = tmp_path / "dest"
        result = move_file(src, dest_dir, new_name="renamed.txt")
        assert result.name == "renamed.txt"


class TestCopyFile:
    def test_copies_file(self, tmp_path: Path):
        src = tmp_path / "source.txt"
        src.write_text("content")
        dest_dir = tmp_path / "dest"
        result = copy_file(src, dest_dir)
        assert result.exists()
        assert src.exists()

    def test_copies_with_new_name(self, tmp_path: Path):
        src = tmp_path / "source.txt"
        src.write_text("content")
        dest_dir = tmp_path / "dest"
        result = copy_file(src, dest_dir, new_name="copied.txt")
        assert result.name == "copied.txt"


class TestOpenInFileManagerGuard:
    def test_missing_path_rejected(self, tmp_path: Path):
        with pytest.raises(RuntimeError, match="does not exist"):
            open_in_file_manager(tmp_path / "nope.pdf")

    def test_executable_suffix_rejected(self, tmp_path: Path):
        for name in ("evil.exe", "run.bat", "click.lnk", "macro.hta", "script.js"):
            target = tmp_path / name
            target.write_bytes(b"x")
            with pytest.raises(RuntimeError, match="executable file type"):
                open_in_file_manager(target)

    def test_case_insensitive_suffix(self, tmp_path: Path):
        target = tmp_path / "EVIL.EXE"
        target.write_bytes(b"x")
        with pytest.raises(RuntimeError, match="executable file type"):
            open_in_file_manager(target)

    def test_nonexistent_exe_rejected(self, tmp_path: Path):
        target = tmp_path / "evil.exe"
        with pytest.raises(RuntimeError, match="does not exist"):
            open_in_file_manager(target)


class TestMonthArchiveFolder:
    def test_january(self, tmp_path: Path):
        result = month_archive_folder(tmp_path, date(2026, 1, 15))
        assert result.name == "January_2026"

    def test_december(self, tmp_path: Path):
        result = month_archive_folder(tmp_path, date(2026, 12, 25))
        assert result.name == "December_2026"

    def test_default_today(self, tmp_path: Path):
        result = month_archive_folder(tmp_path)
        today = date.today()
        months = (
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        )
        assert result.name == f"{months[today.month - 1]}_{today.year}"


class TestIsImagePdf:
    def test_is_image(self, tmp_path: Path):
        assert is_image(tmp_path / "photo.jpg")
        assert is_image(tmp_path / "photo.PNG")
        assert not is_image(tmp_path / "doc.pdf")

    def test_is_pdf(self, tmp_path: Path):
        assert is_pdf(tmp_path / "doc.pdf")
        assert is_pdf(tmp_path / "doc.PDF")
        assert not is_pdf(tmp_path / "doc.txt")
