# openJiuwen Agent Core — HydroQuote usage

See also `migration-package/02_OpenJiuwen_Agent_Core_使用纲要.md`.

## Status on this workspace

- Host Python **3.14**: `openjiuwen` / `workswarm` may be unavailable (workswarm requires `<3.14`).
- Adapters in `hydroquote/agent_core/` attempt real Workflow construction when import succeeds.
- If unavailable, deterministic domain extract/selection runs; `agent_core_backend=deterministic_fallback` is traced.
- **Do not claim real WorkflowAgent production verification** until installed on Python 3.11–3.13 with model credentials.

## Intended wiring

1. `InquiryAgentAdapter.extract` → LangGraph `inquiry` node  
2. `EngineeringAgentAdapter.fast_select` → `fast_quote` node (rules via Tool/domain)  
3. `QuotationAgentAdapter.describe` → commercial description only (no arithmetic)

LangGraph owns pause/resume (`needs_input`) and quote_id/thread_id persistence via QuoteStore + MemorySaver checkpoint.
