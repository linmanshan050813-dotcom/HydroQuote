# HydroQuote migration report

- **Branch:** `feature/langgraph-jiuwenswarm-mcp`
- **Date:** 2026-11-03
- **Push/merge/deploy:** No (not authorized)

## Modified / added (summary)

- `migration-package/` — copied implementation specs + contracts
- `hydroquote/` — contracts, domain, agent_core, orchestration, swarm, application, mcp
- `config/pricing_rules.yaml`, `config/complexity_rules.yaml`
- `app/main.py` — remove `random.uniform`; domain engine; `/api/v2/quote*`; MCP mount
- `docs/BASELINE_AUDIT.md`, `RULES_DISCREPANCY_LOG.md`, `ARCHITECTURE.md`, `OPENJIUWEN_AGENT_CORE_GUIDE.md`
- `tests/unit|integration|contract` — pricing, router, parallel costs, fast/expert graph, MCP
- `requirements-v2.txt`

## Versions (venv)

- Python: 3.14 (host)
- langgraph: 1.2.19
- mcp: 2.3.0 (MCPServer; FastMCP renamed)
- pydantic: 2.14.2
- openjiuwen: **not installed** (blocker)
- workswarm / jiuwenswarm: **not installable on 3.14** (requires `<3.14`)

## Tests

```text
.\.venv\Scripts\python.exe -m pytest tests/unit tests/integration tests/contract -q
17 passed
```

## Evidence checklist

| Item | Status |
|------|--------|
| Fast route real LangGraph trace | **Pass** (`test_fast_quote_no_swarm`) — no Swarm |
| Expert route without Swarm available | **Pass** — `review_required`, no Fast fallback (`test_expert_graph`) |
| Real JiuwenSwarm Team 4-expert run | **Blocked** — Python 3.14 / no workswarm CLI |
| Real openJiuwen WorkflowAgent model call | **Blocked** — package/runtime |
| Turbine golden 2×1200 Francis = 108000 | **Pass** |
| Five-item parallel costing | **Pass** |
| MCP tool list = only `hydroquote_quote` | **Pass** (MCPServer.list_tools) |
| Customer payload no internal cost | **Pass** |
| Unauthorized submit_review | **Pass** |
| Human approval pause/resume (LangGraph interrupt) | **Partial** — review via `submit_review` + re-run; MemorySaver checkpointer present; durable DB checkpointer not productionized |
| Firm PI with bank/HS | **Partial** — preliminary PI generated; firm requires full PI fields |

## Remaining blockers / unapproved business rules

- See `docs/RULES_DISCREPANCY_LOG.md` (personnel table vs formula; risk reserve default; price bands)
- Install Python 3.11–3.13 + `openjiuwen` + `workswarm` for real Expert/Agent Core demos
- Set `HYDROQUOTE_SWARM_ENABLED=true` and run `jiuwenswarm` for Team evidence
- Production auth (OAuth), durable checkpointer, A2A Swarm gateway — not claimed done

## Legacy

- Prompt-only / watsonx-only architecture docs: treat as **Legacy/Deprecated** relative to this LangGraph design.
