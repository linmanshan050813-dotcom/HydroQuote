"""LangGraph HydroQuoteState."""

from __future__ import annotations

from typing import Any, Literal, Optional, TypedDict


class HydroQuoteState(TypedDict, total=False):
    quote_id: str
    request_id: str
    tenant_id: str
    status: str
    workflow_stage: str
    raw_input_ref: str
    project_text: str
    inquiry: dict
    confirmed: bool
    missing_fields: list[str]
    conflict_flags: list[str]
    routing_path: Literal["fast_quote", "expert_quote"]
    routing_reasons: list[str]
    technical_package: dict
    expert_run_id: str
    expert_records: list[dict]
    equipment_costs: dict
    cost_breakdown: dict
    project_additional_cost: str
    internal_cost: str
    commercial_quote: dict
    pi_artifact: dict
    pi_fields: dict
    rule_version: str
    warnings: list[str]
    human_review: dict
    trace_id: str
    trace: list[dict]
    error: Optional[str]
    swarm_called: bool
    agent_core_invoked: bool
