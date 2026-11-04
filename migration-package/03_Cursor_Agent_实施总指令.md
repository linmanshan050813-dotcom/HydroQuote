# Cursor Agent — HydroQuote v2 implementation task (paste directly into Cursor Agent)

You are the **primary and only coding agent** working inside the existing HydroQuote repository. You may inspect files, edit code, run tests and produce implementation evidence using Cursor's own Agent capabilities. Do not delegate to another coding assistant or wait for a separate controller.

Repository: `https://github.com/linmanshan050813-dotcom/HydroQuote` (operate on the currently opened local workspace). Create an isolated feature branch `feature/langgraph-jiuwenswarm-mcp`; never push, merge, rewrite history or deploy without explicit approval.

## Read all project requirements FIRST

Read the entire `migration-package/` including:

- `00_README_使用说明.md`
- `01_HydroQuote_完整重构方案.md`
- `02_OpenJiuwen_Agent_Core_使用纲要.md`
- `04_JiuwenSwarm_复杂选型集成.md`
- `05_LangGraph_编排与状态设计.md`
- `06_MCP_单一外部接口.md`
- `07_验收测试矩阵.md`
- `architecture/HydroQuote_Workflow.mmd`
- every JSON file under `contracts/`.

Also inspect the repository's original business source documents (`总流程设计.docx`, `Agent报价流程设计.docx`, `报价规则.docx`, `报价单案例.docx`, preferably in `Planning Docs/` or provided separately). Treat these source specifications as authoritative over obsolete demo pricing in the README. Build a discrepancy log without silently modifying the source rules.

Verify your actual pinned library versions against **official** LangGraph, openJiuwen Agent Core, JiuwenSwarm and MCP docs; do not invent API imports or runtime interfaces. Report any version incompatibilities with a reproducible traceback and a tested correction.

## Non-negotiable architecture

**LangGraph is the sole top-level business orchestrator** with durable quotation state, routing, parallel work, retries, human interrupts/resumes and execution trace.

The graph must execute EXACTLY these business stages:

1. `Customer Inquiry — Agent + Workflow`: parse uploaded documents/text, extract and normalize parameters, ask for missing information, obtain customer confirmation, and only then classify the inquiry.
2. `Technical Selection`: deterministic **Fast Quote** for standard projects OR **Expert Quote using a real JiuwenSwarm Agent Team** for complex projects.
3. Both paths produce one validated `TechnicalSelectionPackage` after physics/rule/schema checks, and human approval when necessary.
4. `Engineering Cost — Workflow`: five parallel component calculations (Turbine, Generator+AVR, Governor, Inlet Valve, Automation); join results once, calculate project additional cost, risk reserve and internal cost.
5. `Commercial Quotation — Workflow`: apply the exact commercial formula, internal cost × 2.40.
6. `PI Generation — Workflow`: fill validated template, prevent invented contract/bank/HS/delivery terms, generate authorized downloadable files, and return Technical Proposal + Quotation + PI.

**openJiuwen Agent Core** must be used for genuine, testable specialist `WorkflowAgent`/component execution (Inquiry/Engineering and Quotations support), but MUST NOT implement a second top-level end-to-end workflow that conflicts with LangGraph.

**JiuwenSwarm** must be used ONLY for the complex **technical selection** branch, not a blanket post-quote commercial review. Team roles: `Hydraulic Expert`, `Equipment Expert`, `Operations Expert`, `Risk Reviewer`, coordinated by a Leader. Require independent assessments → discussion → cross-review → a structured Technical Selection Package. No expert has permission to alter pricing formulas.

**MCP external integration:** exactly ONE publicly exposed Streamable HTTP `/mcp` endpoint, with ONE public tool `hydroquote_quote`. It accepts `create`, `revise`, `get`, `submit_review` in one versioned contract. Do not create a separate public tool for each business calculation. Existing web API may remain for backward compatibility, delegating to the same `QuotationApplication` service.

## Implementation details that must be real

- Replace the old demo pricing path (`random.uniform`, generic $/kW pricing) with pure, deterministic Python domain functions and `Decimal`. Keep the established five equipment items and the exact pre-existing pricing formulas, risk reserve rule + 8% after-sales and ×2.40 commercial multiplier.
- Any unresolved/contradictory business numbers or missing approved risk reserve must be marked `review_required`; DO NOT fabricate precise price bands, supplier prices, bank details, HS codes, delivery terms, or other commercial facts.
- Extract technical routing into an independently testable and versioned `complexity_rules` module. Missing essential input → `needs_input`, not automatically Swarm. Document all Fast vs Expert reasons, and separate technical expert routing from pricing-rule approval.
- Use a real LangGraph `StateGraph` with conditional edges (or tested equivalent), persisted `thread_id`, human-in-the-loop interrupts and resume, explicit error states and idempotent retry behavior. Do not store only one giant unvalidated prompt string as state.
- Agent Core must be invoked in genuine runtime business nodes (not just in unused examples). Do not run nested duplicate global orchestrators.
- Implement JiuwenSwarm integration with an actually tested `SwarmAdapter`. For a local proof of concept, the documented `jiuwenswarm chat --mode team --session <id> --json --timeout <seconds> "..."` CLI can be used via a **safe subprocess argument vector (no shell injection)**, serialized access / concurrency cap due to its shared TUI channel. Verify actual CLI support in the installed version. For production, assess the official A2A Gateway as a proper service integration; never invent an unverified Python import API.
- Ensure JiuwenSwarm can use an authorized MCP `get` call for a complex case; implement role-specific review data, trace real tool invocation, and ensure it cannot call `create` recursively or `submit_review` with elevated privileges. Parse the returned JSON and validate against the internal Technical Selection Package schema. If Team is unavailable, explicitly return a review/pending status without faking an expert result.
- Parallel price calculation must truly fan out five work items (LangGraph `Send` or safe parallel Python operations within LangGraph) and reduce exactly once. Any missing cost must block a firm quote. Include failures/cancel/retry tests.
- Keep FastAPI, frontend, text/PDF/DOCX upload and PI download behavior unless a change is unavoidable and explicitly documented. Correct invalid `.doc` assumptions if unsupported, add file limits, secure downloads and API error messages.
- MCP tools are exposed via official Python `FastMCP` SDK with auth at transport/gateway and application permission checks, strict schemas, tenant isolation, idempotency, timeouts, input limits and an independent client test. Never expose internal cost or supplier price in ordinary external responses.
- QuoteStore must persist request/approval state across reloads, including LangGraph checkpoint data where required. Use a durable store or a documented single-instance MVP adapter. Secure audit logs; do not log secrets, private raw customer documents or API credentials.
- Secret scan source and history. **Do not display, commit or paste credentials found in local private documents**. Provide sanitized `.env.example` and protect tracked secrets; report any leaked key for owner rotation.

## Required execution order — do not stop after planning

**P0 — Baseline**: inspect current code and files, run current checks, create feature branch, write `docs/BASELINE_AUDIT.md` and `docs/RULES_DISCREPANCY_LOG.md`.

**P1 — Pure domain**: implement Pydantic contracts, hydraulic/selection/pricing business functions, rule versioning, strict validation, and tests (including the original 2 × 1200 kW Francis cost example = USD 108,000 for turbine cost only).

**P2 — Global graph + Agent Core**: build and execute real LangGraph graph with Inquiry Agent Core WorkflowAgent, `needs_input` pause/resume, Fast Quote route and unified technical package. Add traces and tests.

**P3 — Expert branch**: build a 4-expert JiuwenSwarm Team and a functioning SwarmAdapter, verify a real Team run and structured results. Integrate ONLY as LangGraph `expert_quote` node, not for fast cases.

**P4 — Cost/Commercial/PI**: implement five equipment parallel fan-out & join, additional cost, risk/internal cost, commercial multiplier, template rendering, human price/engineering gates.

**P5 — One public MCP and web integration**: implement one tool and test with independent MCP Client; integrate existing UI and FastAPI into the same application service. Restrict access to internal quote economics.

**P6 — Acceptance and docs**: complete unit/contract/integration/E2E/security regression matrix, setup/runbook, architecture, OpenJiuwen guide, migration report and no-sensitive-data demonstration traces. Note real services/tests that could not run due to missing credentials or runtime access.

## Critical acceptance cases

- A confirmed standard project travels `inquiry -> fast_quote -> technical_validation -> engineering_cost (5 parallel entries) -> commercial -> PI`, with NO JiuwenSwarm run.
- A complex project travels `inquiry -> expert_quote (4 real specialists) -> independent opinions/discussion/cross-review -> TechnicalSelectionPackage -> technical_validation -> engineering_cost -> commercial -> PI` (with human gate when needed).
- Missing essential parameters result in `needs_input` and resume correctly without duplicate invoices or price calculations.
- Every stage persists typed state and an audit-friendly trace with rule/model/tool version and no secrets.
- Same inputs + same approved rule version yield identical prices; `random.uniform` never changes a quote.
- Exact 5 main equipment items, correct quantity, no invented risk rate and no fabricated missing contract values.
- Only one MCP Tool appears in `tools/list`, and authenticated `tools/call` works from a separate process; unauthorized/other-tenant requests fail.
- A real standard and complex PI artifact is produced only after correct technical/commercial approval gates; any blocked stage remains visibly pending.
- Agent Core `WorkflowAgent` and JiuwenSwarm Team must be **actually invoked** on the relevant runtime path, not merely referenced by README or imports.

## Reporting instructions

Implement iteratively with actual code changes and test executions. Maintain a phase-by-phase concise progress log in `docs/MIGRATION_REPORT.md`, including changed files, commands executed, passing/failing tests and blockers. Do not claim success if only mock tests passed. No push/merge/deploy without explicit user authorization.

Start now with repository audit, version compatibility verification, and P0; then proceed through P6 within available tools and access. Do not ask for clarifications whose answers already exist in the source docs; log unresolved **business approval** items and safely mark `review_required` instead.
