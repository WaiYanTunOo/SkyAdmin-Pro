# Document Hub — Feature Detail

## Purpose
Folder/document workflows: renamer, image-to-PDF, agent bundle, portal, archive, financial. Lazy panels; polling pauses when hidden.

## Code Files

| Layer | File | Key symbols |
|-------|------|-------------|
| View | `skyadmin_pro/ui/views/document_hub/view.py` | `DocumentHubView`, 3s poll, `on_hide()` pause |
| Renamer | `skyadmin_pro/ui/views/document_hub/renamer.py` | Batch file renamer tool |
| Image/PDF | `skyadmin_pro/ui/views/document_hub/image_pdf.py` | Image → PDF conversion |
| Agent Bundle | `skyadmin_pro/ui/views/document_hub/agent_bundle.py` | Agent file bundling |
| Portal | `skyadmin_pro/ui/views/document_hub/portal.py` | Client portal ops |
| Archive | `skyadmin_pro/ui/views/document_hub/archive.py` | Archive/unarchive |
| Financial | `skyadmin_pro/ui/views/document_hub/financial.py` | Financial document tools |
| Helpers | `skyadmin_pro/ui/views/document_hub/helpers.py` | Shared utility funcs |
| Services | `skyadmin_pro/services/file_ops.py` | Copy/sanitize/open paths |
| Config | `skyadmin_pro/config/documents.py` | `FINANCIAL_DOC_*`, `IMAGE_SUFFIXES`, `PDF_SUFFIX` |

## Architecture Decisions
- **Lazy panel init** (Phase 9.2): each tool panel built on first visit.
- **Polling**: 3s refresh only while visible — `on_hide()` cancels; acceptable disk I/O for local files.
- **Async operations**: long file jobs run via `services/process_jobs.py` with FeedbackLabel error surfacing.

## Tests

| File | Covers |
|------|--------|
| `tests/test_document_hub_polling.py` | Poll pause on hide, resume on show |

## Roadmap Status

| Phase | Item | Status |
|-------|------|--------|
| Phase 9.2 | Lazy-init each tool panel | ✅ Landed |
| Phase 7.4 | Background thread error surfacing | ✅ Landed |
| Phase 9C | Empty states, loading states | ✅ Landed |

## Known Fix Locations

| Issue | File:Line | Priority |
|-------|-----------|----------|
| 3s polling includes os.listdir + stat I/O | `view.py:147–152` | P3 (cache if network drives) |
| 6 tool panels historically in one file (~1100 lines) | `view.py` | ✅ Split done |
