# Export & Reports — Feature Detail

## Purpose
Excel export with column redaction, PDF report generation, data import.

## Code Files

| Layer | File | Key symbols |
|-------|------|-------------|
| Export | `skyadmin_pro/services/export.py` | `export_to_excel()`, `FORBIDDEN_EXPORT_COLUMNS`, `_assert_export_columns_safe()` |
| Reports | `skyadmin_pro/services/reports.py` | Report generation |
| PDF render | `skyadmin_pro/services/pdf_render.py` | PDF rendering helpers |
| Import | `skyadmin_pro/services/importer.py` | Data import utilities |
| Config | `skyadmin_pro/config/documents.py` | `FINANCIAL_DOC_*`, doc type mappings |

## Architecture Decisions
- **Atomic writes**: temp + rename pattern (no partial files).
- **Column redaction**: `FORBIDDEN_EXPORT_COLUMNS` set prevents export of sensitive columns.
- **Runtime guard**: `_assert_export_columns_safe()` checks DataFrame columns ⊆ allowed set (Phase 8.4 landed).
- **OpenPyXL**: no pandas dependency for export.

## Tests

| File | Covers |
|------|--------|
| `tests/test_export_security.py` | Column redaction, forbidden columns |
| `tests/test_export_supplier.py` | Supplier export |
| `tests/test_export_visible.py` | Export visible columns |
| `tests/test_reports.py` | Report generation |
| `tests/test_importer.py` | Data import |

## Roadmap Status

| Phase | Item | Status |
|-------|------|--------|
| Phase 8.4 | Export runtime column guard | ✅ Landed |
| Wave B F1.6 | Print-ready reports (PDF + tax overview) | ✅ Landed |

## Known Fix Locations

| Issue | File:Line | Priority |
|-------|-----------|----------|
| Acceptable — no known issues | — | — |
