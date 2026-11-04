# HydroQuote v2 — Baseline Audit (P0)

**Branch:** `feature/langgraph-jiuwenswarm-mcp`  
**Date:** 2026-11-03  
**Workspace:** `OIOteam_IBM_hackathon-main`

## Pre-migration snapshot

| Item | Finding |
|------|---------|
| Layout | FastAPI monolith in `app/main.py` (~564 lines); `frontend/index.html` wizard |
| Pricing | Demo heuristic: `capacity_kw * $/kW` + `random.uniform(0.95, 1.05)`; PI splits equipment by fixed ratios (46/29/11/08/rest) |
| Deterministic rules | Documented in README / `Planning Docs/报价规则.docx` but **not implemented** in code |
| LangGraph / Agent Core / JiuwenSwarm / MCP | **Absent** |
| `hydroquote/` package | **Absent** (created in this migration) |
| Planning Docs | Present: `报价规则.docx`, `Agent报价流程设计.docx`, `总流程设计.docx`, `报价单案例.docx` |
| Secrets | `.env` exists locally (gitignored); `.env.example` uses placeholders only — no credentials committed in this audit |

## Runtime / dependency compatibility

| Package | Status on this machine |
|---------|------------------------|
| Python | Host default **3.14**; `workswarm` requires `>=3.11,<3.14` → **blocked for real JiuwenSwarm install** |
| `langgraph` | Installable; pin recorded in `requirements-v2.txt` after freeze |
| `mcp` | Installable |
| `openjiuwen` | Attempted; may fail on 3.14 — adapters include fallback / mock path; real invoke marked blocked if import fails |
| `workswarm` / `jiuwenswarm` CLI | **Not installable on Python 3.14** — Expert Quote uses adapter with honest `review_required` when CLI unavailable |

## Legacy API surface (must remain compatible)

- `GET /`, `/health`, `/config/info`
- `POST /api/analyze-project`
- `POST /api/generate-proforma-invoice`

## Security notes

- Do not commit `.env` or paste live API keys into docs/traces.
- Migration package copied to `migration-package/` (no secrets).
- Health endpoint historically requires Watson NLU; v2 keeps endpoint but quotation path must not depend on NLU for deterministic costing.
