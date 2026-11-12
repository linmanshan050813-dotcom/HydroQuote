"""Stable task templates for JiuwenSwarm Expert Quote (no customer PII / costs)."""

from __future__ import annotations


def build_team_prompt(
    quote_id: str,
    routing_reasons: list[str],
    rule_version: str,
    *,
    discuss_timeout_s: int,
) -> str:
    reasons = "; ".join(routing_reasons) or "complex_project"
    return (
        f"Review HydroQuote complex inquiry quote_id={quote_id}; "
        f"routing_reasons=[{reasons}]; engineering_rules_version={rule_version}. "
        "Use connected MCP get (read-only) for allowed technical data only. "
        "Have four experts independently analyze (Hydraulic Expert, Equipment Expert, "
        "Operations Expert, Risk Reviewer), then discuss and cross-review. "
        f"The discussion budget is {discuss_timeout_s} seconds. "
        "A follow-up message that starts with LEADER_CLOSE means that budget is over. "
        "Swarm Leader must then stop every expert immediately and return ONLY "
        "a TechnicalSelectionPackage JSON. That JSON is the AI decision: pick one scheme "
        "from opinions already given. Set readiness to preliminary_ready and "
        "technical_approval_required to true. Add a risk note that the leader closed "
        "the meeting at the time limit. "
        "Include recommended_turbine_type, unit_count, unit_capacity_kw, "
        "hydraulic_calculation, equipment_scope (five main items), expert_opinions (four), "
        "discussion_summary, cross_review, assumptions, risk_notes, readiness, "
        "technical_approval_required. "
        "If net head or design flow is missing, set readiness to needs_human_review "
        "and do not invent those values. "
        "Do not price or approve commercial quotes. Do not call create/revise/submit_review. "
        "Do not start another expert round after LEADER_CLOSE."
    )


def build_leader_decision_prompt(quote_id: str, routing_reasons: list[str], rule_version: str) -> str:
    """Same session, after the discussion budget. Leader decides; experts do not continue."""
    reasons = "; ".join(routing_reasons) or "complex_project"
    return (
        "LEADER_CLOSE. Discussion time is over. Do not kill the meeting without a decision. "
        f"Swarm Leader only, for quote_id={quote_id}; routing_reasons=[{reasons}]; "
        f"engineering_rules_version={rule_version}. "
        "Stop every expert now. Do not open another analysis round. "
        "Using opinions already in this session and read-only MCP get, choose one technical "
        "scheme and return ONLY a TechnicalSelectionPackage JSON with recommended_turbine_type, "
        "unit_count, unit_capacity_kw, hydraulic_calculation, equipment_scope (five main items), "
        "expert_opinions (four roles: Hydraulic Expert, Equipment Expert, Operations Expert, "
        "Risk Reviewer), discussion_summary, cross_review, assumptions, risk_notes, "
        "readiness=preliminary_ready, technical_approval_required=true, selection_path=expert_quote. "
        "Record in risk_notes that the leader closed the meeting at the time limit. "
        "If net head or design flow is missing, set readiness to needs_human_review and do not "
        "invent those values. Do not price. Do not call create/revise/submit_review."
    )
