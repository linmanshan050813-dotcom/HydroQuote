"""LangGraph StateGraph — sole top-level HydroQuote orchestrator."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Literal, Optional

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from hydroquote.agent_core.engineering_workflow import EngineeringAgentAdapter
from hydroquote.agent_core.inquiry_workflow import InquiryAgentAdapter
from hydroquote.agent_core.quotation_workflow import QuotationAgentAdapter
from hydroquote.contracts.models import InquiryData, TechnicalSelectionPackage
from hydroquote.domain.equipment import validate_five_equipment
from hydroquote.domain.hydraulic import check_hydraulic
from hydroquote.domain.pi import build_pi_document, pi_readiness
from hydroquote.domain.pricing import PricingEngine
from hydroquote.orchestration.approval import needs_price_gate, needs_technical_gate
from hydroquote.orchestration.cost_fanout import parallel_equipment_costs
from hydroquote.orchestration.latency import attribute_wait
from hydroquote.orchestration.router import route_after_inquiry
from hydroquote.orchestration.state import HydroQuoteState
from hydroquote.swarm.adapter import SwarmAdapter

logger = logging.getLogger(__name__)


def _trace(state: HydroQuoteState, event: str, **extra: Any) -> list[dict]:
    trace = list(state.get("trace") or [])
    item = {"event": event, **extra}
    trace.append(item)
    return trace


def _timed_node(name: str, fn):
    """Attach wall-clock milliseconds to the node's last trace event."""

    async def wrapped(state: HydroQuoteState) -> dict:
        started = time.perf_counter()
        out = await fn(state)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        trace = out.get("trace")
        if trace:
            trace[-1]["elapsed_ms"] = elapsed_ms
            trace[-1]["node"] = name
        else:
            out["trace"] = _trace(state, name, elapsed_ms=elapsed_ms, node=name)
        return out

    wrapped.__name__ = f"{name}_timed"
    return wrapped


def build_hydroquote_graph(
    *,
    inquiry_adapter: Optional[InquiryAgentAdapter] = None,
    engineering_adapter: Optional[EngineeringAgentAdapter] = None,
    quotation_adapter: Optional[QuotationAgentAdapter] = None,
    swarm_adapter: Optional[SwarmAdapter] = None,
    pricing_engine: Optional[PricingEngine] = None,
    checkpointer: Any = None,
):
    inquiry_adapter = inquiry_adapter or InquiryAgentAdapter()
    engineering_adapter = engineering_adapter or EngineeringAgentAdapter()
    quotation_adapter = quotation_adapter or QuotationAgentAdapter()
    swarm_adapter = swarm_adapter or SwarmAdapter()
    pricing_engine = pricing_engine or PricingEngine()

    async def inquiry_node(state: HydroQuoteState) -> dict:
        text = state.get("project_text") or ""
        # Prefer structured parameters if already present
        if state.get("inquiry") and state.get("confirmed"):
            return {
                "workflow_stage": "customer_inquiry",
                "agent_core_invoked": state.get("agent_core_invoked", False),
                "trace": _trace(state, "inquiry_skip_extract_confirmed"),
            }
        result = await inquiry_adapter.extract(text, conversation_id=state.get("quote_id"))
        merged = dict(state.get("inquiry") or {})
        merged.update({k: v for k, v in result["inquiry"].items() if v is not None})
        return {
            "inquiry": merged,
            "missing_fields": result["missing_fields"],
            "conflict_flags": result["conflict_flags"],
            "agent_core_invoked": result.get("agent_core_invoked", False),
            "workflow_stage": "customer_inquiry",
            "status": "needs_input" if result["missing_fields"] else "processing",
            "trace": _trace(
                state,
                "inquiry_agent_core",
                backend=result.get("agent_core_backend"),
                missing=result["missing_fields"],
                llm_elapsed_ms=result.get("llm_elapsed_ms"),
                llm_attempts=result.get("llm_attempts"),
            ),
        }

    async def validate_inquiry_node(state: HydroQuoteState) -> dict:
        inquiry = InquiryData.model_validate(state.get("inquiry") or {})
        from hydroquote.domain.inquiry import detect_conflicts, missing_required_fields, normalize_units_config

        inquiry = normalize_units_config(inquiry)
        missing = missing_required_fields(inquiry)
        conflicts = detect_conflicts(inquiry)
        confirmed = bool(state.get("confirmed")) and not missing
        status = "needs_input" if missing or not state.get("confirmed") else state.get("status", "processing")
        return {
            "inquiry": inquiry.model_dump(mode="json"),
            "missing_fields": missing,
            "conflict_flags": conflicts,
            "confirmed": confirmed if missing else bool(state.get("confirmed", True)),
            "status": status if missing else ("processing" if state.get("confirmed", True) else "needs_input"),
            "trace": _trace(state, "validate_inquiry", missing=missing, conflicts=conflicts),
        }

    def route_after_validate(
        state: HydroQuoteState,
    ) -> Literal["needs_input", "fast_quote", "expert_quote"]:
        inquiry = InquiryData.model_validate(state.get("inquiry") or {})
        path, _ = route_after_inquiry(inquiry, confirmed=bool(state.get("confirmed")))
        return path

    async def annotate_route(state: HydroQuoteState) -> dict:
        inquiry = InquiryData.model_validate(state.get("inquiry") or {})
        path, reasons = route_after_inquiry(inquiry, confirmed=bool(state.get("confirmed")))
        if path == "needs_input":
            return {
                "status": "needs_input",
                "routing_reasons": reasons,
                "trace": _trace(state, "route_needs_input", reasons=reasons),
            }
        return {
            "routing_path": path,  # type: ignore[typeddict-item]
            "routing_reasons": reasons,
            "workflow_stage": "technical_selection",
            "trace": _trace(state, "route", path=path, reasons=reasons),
        }

    async def fast_quote_node(state: HydroQuoteState) -> dict:
        result = await engineering_adapter.fast_select(state.get("inquiry") or {})
        return {
            "technical_package": result["technical_package"],
            "swarm_called": False,
            "agent_core_invoked": state.get("agent_core_invoked", False)
            or result.get("agent_core_invoked", False),
            "routing_path": "fast_quote",
            "trace": _trace(state, "fast_quote"),
        }

    async def expert_quote_node(state: HydroQuoteState) -> dict:
        swarm_result = await swarm_adapter.run_expert_selection(
            quote_id=state.get("quote_id") or "unknown",
            routing_reasons=list(state.get("routing_reasons") or []),
            rule_version=pricing_engine.rule_version,
        )
        if not swarm_result["ok"] or not swarm_result.get("package"):
            return {
                "swarm_called": True,
                "expert_run_id": swarm_result.get("expert_run_id"),
                "expert_records": [
                    {
                        "error": swarm_result.get("error"),
                        "backend": swarm_result.get("backend"),
                    }
                ],
                "status": "review_required",
                "technical_package": None,
                "routing_path": "expert_quote",
                "warnings": list(state.get("warnings") or [])
                + [f"swarm_failed:{swarm_result.get('error')}"],
                "trace": _trace(
                    state,
                    "expert_quote_failed",
                    error=swarm_result.get("error"),
                    stages=swarm_result.get("stages") or [],
                    # Never fabricate Fast Quote on Swarm failure
                    no_fast_fallback=True,
                ),
            }
        return {
            "technical_package": swarm_result["package"],
            "swarm_called": True,
            "expert_run_id": swarm_result.get("expert_run_id"),
            "expert_records": [{"raw_excerpt": swarm_result.get("raw_excerpt")}],
            "routing_path": "expert_quote",
            "status": "review_required"
            if swarm_result.get("review_required")
            else state.get("status", "processing"),
            "trace": _trace(
                state,
                "expert_quote_ok",
                expert_run_id=swarm_result.get("expert_run_id"),
                stages=swarm_result.get("stages") or [],
            ),
        }

    async def validate_technical_node(state: HydroQuoteState) -> dict:
        pkg = state.get("technical_package")
        if not pkg:
            return {
                "status": "review_required",
                "warnings": list(state.get("warnings") or []) + ["missing_technical_package"],
                "trace": _trace(state, "technical_validation_missing"),
            }
        package = TechnicalSelectionPackage.model_validate(pkg)
        errs = validate_five_equipment(package)
        inquiry = InquiryData.model_validate(state.get("inquiry") or {})
        hydro = check_hydraulic(inquiry)
        review = bool(errs) or package.technical_approval_required or hydro.get("review_required")
        status = state.get("status")
        if review and status not in ("rejected", "error"):
            # keep review_required if already set from swarm failure path with package
            if package.readiness == "needs_human_review" or errs:
                status = "review_required"
        return {
            "technical_package": package.model_dump(mode="json"),
            "status": status or "processing",
            "human_review": {
                **(state.get("human_review") or {}),
                "technical_pending": needs_technical_gate(
                    {"technical_package": package.model_dump(mode="json")}
                ),
                "equipment_errors": errs,
            },
            "trace": _trace(state, "technical_validation", errors=errs, hydro=hydro.get("notes")),
        }

    async def engineering_cost_node(state: HydroQuoteState) -> dict:
        if not state.get("technical_package"):
            return {
                "status": "review_required",
                "trace": _trace(state, "cost_skipped_no_package"),
            }
        # Do not cost if swarm failed without package (already handled)
        inquiry = InquiryData.model_validate(state.get("inquiry") or {})
        technical = TechnicalSelectionPackage.model_validate(state["technical_package"])
        # Parallel fan-out of five lines
        equipment = await parallel_equipment_costs(pricing_engine, inquiry, technical)
        breakdown = pricing_engine.compute_breakdown(inquiry, technical)
        # Prefer parallel line results for equipment_costs field (same formulas)
        bd = breakdown.model_dump(mode="json")
        bd["equipment_costs"] = equipment
        status = "review_required" if breakdown.review_required else "preliminary"
        return {
            "equipment_costs": equipment,
            "cost_breakdown": bd,
            "project_additional_cost": str(breakdown.project_additional_cost),
            "internal_cost": str(breakdown.internal_cost) if breakdown.internal_cost is not None else None,
            "workflow_stage": "engineering_cost",
            "status": status,
            "rule_version": breakdown.rule_version,
            "trace": _trace(
                state,
                "engineering_cost_parallel",
                keys=list(equipment.keys()),
                review=breakdown.review_required,
                reasons=breakdown.review_reasons,
            ),
        }

    async def commercial_node(state: HydroQuoteState) -> dict:
        cost = state.get("cost_breakdown") or {}
        if cost.get("review_required") or cost.get("commercial_quotation") is None:
            return {
                "workflow_stage": "commercial_quotation",
                "status": "review_required",
                "commercial_quote": {
                    "status": "pending_review",
                    "reasons": cost.get("review_reasons"),
                },
                "trace": _trace(state, "commercial_pending_review"),
            }
        desc = await quotation_adapter.describe(cost, state.get("technical_package") or {})
        commercial = {
            "total_usd": cost.get("commercial_quotation"),
            "multiplier": "2.40",
            "description": desc,
            "rule_version": cost.get("rule_version"),
        }
        return {
            "commercial_quote": commercial,
            "workflow_stage": "commercial_quotation",
            "status": "preliminary",
            "trace": _trace(state, "commercial_ok", total=commercial["total_usd"]),
        }

    async def pi_node(state: HydroQuoteState) -> dict:
        cost_raw = state.get("cost_breakdown")
        tech_raw = state.get("technical_package")
        if not cost_raw or not tech_raw:
            return {
                "status": "review_required",
                "pi_artifact": {"status": "blocked"},
                "trace": _trace(state, "pi_blocked"),
            }
        from hydroquote.contracts.models import CostBreakdown

        inquiry = InquiryData.model_validate(state.get("inquiry") or {})
        technical = TechnicalSelectionPackage.model_validate(tech_raw)
        # Rebuild typed cost from parallel equipment + pricing engine for consistency
        cost = pricing_engine.compute_breakdown(inquiry, technical)
        pi_fields = state.get("pi_fields") or {}
        ok, missing = pi_readiness(pi_fields)
        firm = (
            not cost.review_required
            and cost.commercial_quotation is not None
            and ok
            and not needs_technical_gate(state)
            and not needs_price_gate({"cost_breakdown": cost.model_dump(mode="json")})
        )
        try:
            blob = build_pi_document(
                inquiry, technical, cost, pi_fields, firm=firm
            )
            artifact = {
                "status": "ready" if firm else "preliminary",
                "firm": firm,
                "missing_fields": missing,
                "size_bytes": len(blob),
                "content_b64_placeholder": True,
            }
            # Store bytes separately via application layer; keep size in state
            status = "ready" if firm else ("review_required" if cost.review_required or not ok else "preliminary")
            return {
                "pi_artifact": artifact,
                "_pi_bytes": blob,  # application may pop
                "workflow_stage": "completed" if firm else "pi_generation",
                "status": status,
                "cost_breakdown": cost.model_dump(mode="json"),
                "trace": _trace(state, "pi_generated", firm=firm, missing=missing),
            }
        except ValueError as exc:
            return {
                "pi_artifact": {"status": "blocked", "error": str(exc)},
                "status": "review_required",
                "trace": _trace(state, "pi_error", error=str(exc)),
            }

    builder = StateGraph(HydroQuoteState)
    builder.add_node("inquiry", _timed_node("inquiry", inquiry_node))
    builder.add_node("validate", _timed_node("validate", validate_inquiry_node))
    builder.add_node("annotate_route", _timed_node("annotate_route", annotate_route))
    builder.add_node("fast_quote", _timed_node("fast_quote", fast_quote_node))
    builder.add_node("expert_quote", _timed_node("expert_quote", expert_quote_node))
    builder.add_node("technical_validation", _timed_node("technical_validation", validate_technical_node))
    builder.add_node("engineering_cost", _timed_node("engineering_cost", engineering_cost_node))
    builder.add_node("commercial", _timed_node("commercial", commercial_node))
    builder.add_node("pi", _timed_node("pi", pi_node))

    builder.add_edge(START, "inquiry")
    builder.add_edge("inquiry", "validate")
    builder.add_edge("validate", "annotate_route")

    def after_annotate(
        state: HydroQuoteState,
    ) -> Literal["needs_input", "fast_quote", "expert_quote"]:
        if state.get("status") == "needs_input" or state.get("missing_fields"):
            return "needs_input"
        return state.get("routing_path") or route_after_validate(state)  # type: ignore[return-value]

    builder.add_conditional_edges(
        "annotate_route",
        after_annotate,
        {
            "needs_input": END,
            "fast_quote": "fast_quote",
            "expert_quote": "expert_quote",
        },
    )
    builder.add_edge("fast_quote", "technical_validation")
    builder.add_edge("expert_quote", "technical_validation")

    def after_technical(state: HydroQuoteState) -> Literal["engineering_cost", "end_review"]:
        if not state.get("technical_package"):
            return "end_review"
        # If human technical gate hard-required and not approved, still allow cost for preliminary?
        # Spec: only after validation or human approval enter cost. If needs_human_review readiness, pause.
        pkg = state.get("technical_package") or {}
        hr = state.get("human_review") or {}
        if pkg.get("readiness") == "needs_human_review" and not (hr.get("last_decision") == "approve"):
            return "end_review"
        return "engineering_cost"

    builder.add_conditional_edges(
        "technical_validation",
        after_technical,
        {"engineering_cost": "engineering_cost", "end_review": END},
    )
    builder.add_edge("engineering_cost", "commercial")
    builder.add_edge("commercial", "pi")
    builder.add_edge("pi", END)

    memory = checkpointer if checkpointer is not None else MemorySaver()
    return builder.compile(checkpointer=memory)


async def run_quotation_graph(
    graph,
    *,
    quote_id: str,
    request_id: str,
    tenant_id: str,
    project_text: str = "",
    inquiry: Optional[dict] = None,
    confirmed: bool = True,
    pi_fields: Optional[dict] = None,
    thread_id: Optional[str] = None,
) -> HydroQuoteState:
    thread_id = thread_id or quote_id
    init: HydroQuoteState = {
        "quote_id": quote_id,
        "request_id": request_id,
        "tenant_id": tenant_id,
        "project_text": project_text,
        "inquiry": inquiry or {},
        "confirmed": confirmed,
        "status": "processing",
        "workflow_stage": "customer_inquiry",
        "trace_id": f"tr-{uuid.uuid4().hex[:12]}",
        "trace": [],
        "swarm_called": False,
        "agent_core_invoked": False,
        "warnings": [],
        "pi_fields": pi_fields or {},
    }
    config = {"configurable": {"thread_id": thread_id}}
    result = dict(await graph.ainvoke(init, config=config))
    report = attribute_wait(list(result.get("trace") or []))
    result["latency"] = report
    if report.get("slow"):
        logger.warning(
            "slow quote %s cause=%s stage=%s ms=%s share=%s",
            quote_id,
            report.get("cause"),
            report.get("dominant_stage"),
            report.get("dominant_ms"),
            report.get("share"),
        )
    return result  # type: ignore[return-value]
