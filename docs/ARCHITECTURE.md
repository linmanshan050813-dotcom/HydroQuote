# HydroQuote v2 Architecture

## Orchestration ownership

| Layer | Role |
|-------|------|
| **LangGraph** (`hydroquote/orchestration/graph.py`) | Sole top-level workflow: inquiry → Fast/Expert selection → validate → parallel cost → commercial → PI; checkpoints; routing |
| **openJiuwen Agent Core** (`hydroquote/agent_core/`) | Specialist sub-workflows (inquiry extract, fast explanation, quotation text). Not a second orchestrator |
| **JiuwenSwarm** (`hydroquote/swarm/`) | Expert Quote technical selection only (4 experts + leader via CLI adapter) |
| **Python Domain** (`hydroquote/domain/`) | Hydraulic check, selection rules, Decimal pricing, PI template — only money authority |
| **MCP** (`hydroquote/mcp/server.py`) | One tool `hydroquote_quote` on `/mcp` |
| **FastAPI** (`app/main.py`) | Compatibility UI APIs + `/api/v2/quote*`; delegates to `QuotationApplication` |

## Flow

```
MCP / Web → QuotationApplication → LangGraph StateGraph
  → InquiryAgentAdapter
  → complexity_rules (fast | expert | needs_input)
  → Fast rules OR SwarmAdapter
  → TechnicalSelectionPackage validation
  → asyncio.gather × 5 equipment costs
  → additional + risk + ×2.40
  → PI (firm only when terms + rates approved)
```

## Config

- `config/pricing_rules.yaml` — versioned money rules
- `config/complexity_rules.yaml` — Fast vs Expert signals

## Security

- External responses strip internal cost / risk rate / supplier prices
- `tenant_id` from token map (`HYDROQUOTE_TOKENS`), not client-authoritative in production design
- Swarm may `get` technical fields only (`role=swarm`)
