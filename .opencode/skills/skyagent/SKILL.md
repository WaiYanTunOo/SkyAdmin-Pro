---
name: skyagent
description: Use when working with SkyAgent — data-first SQLite+RAG answers, optional HTTPS LLM refine, chat panel, or read-only DB for account admins.
---

# SkyAgent Skill

## Key Files

- `skyadmin_pro/services/skyagent/_router.py` — `answer(query, db, rag, llm=None)` data-first cascade
- `skyadmin_pro/services/skyagent/_https_llm.py` — optional `HttpsLLMProvider` (stdlib urllib)
- `skyadmin_pro/services/skyagent/readonly.py` — `SkyAgentDB` SELECT-only wrapper
- `skyadmin_pro/services/skyagent/rag.py` — BM25 `RAGIndex`
- `skyadmin_pro/services/skyagent/_sql_validator.py` — rejects mutating SQL keywords
- `skyadmin_pro/ui/views/skyagent/` — chat panel (no grab_set; transient + lift)
- `SKYAGENT_INSTRUCTIONS.md` — product rules

## Data-first cascade

1. Bias DB: `pending` → `get_pending_tasks`; `overdue` → `get_overdue_documents`; else `search_clients`
2. If DB hits → local context bullets
3. Else BM25 RAG on docs
4. Else return `No matching data found in SkyAdmin` (never invent)
5. If context and optional HTTPS LLM healthy → `summarize` with **only** that context; on failure → local format

## Package constraints

- No bundled models / Ollama / torch / transformers / llama-cpp
- Product chat must not show MockProvider "Received N chars"
- Env for online: `SKYAGENT_LLM_URL` (https required), `SKYAGENT_LLM_API_KEY`, `SKYAGENT_LLM_MODEL`

## Conventions

- Wave D7: keep new/touched skyagent modules under ~100 lines
- Tests: `tests/test_skyagent_*.py` — MockProvider OK in tests only
- Hotkey: Ctrl+Shift+A → `MainWindow.open_skyagent()`
