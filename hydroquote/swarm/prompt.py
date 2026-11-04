"""Stable task templates for JiuwenSwarm Expert Quote (no customer PII / costs)."""

from __future__ import annotations


def build_team_prompt(quote_id: str, routing_reasons: list[str], rule_version: str) -> str:
    reasons = "; ".join(routing_reasons) or "complex_project"
    return (
        f"Review HydroQuote complex inquiry quote_id={quote_id}; "
        f"routing_reasons=[{reasons}]; engineering_rules_version={rule_version}. "
        "Use connected MCP get (read-only) for allowed technical data only. "
        "Have four experts independently analyze (Hydraulic Expert, Equipment Expert, "
        "Operations Expert, Risk Reviewer), then discuss, cross-review, and return ONLY "
        "a TechnicalSelectionPackage JSON with recommended_turbine_type, unit_count, "
        "unit_capacity_kw, hydraulic_calculation, equipment_scope (five main items), "
        "expert_opinions (four), discussion_summary, cross_review, assumptions, "
        "risk_notes, readiness, technical_approval_required. "
        "Do not invent net head or flow. Do not price or approve commercial quotes. "
        "Do not call create/revise/submit_review."
    )
