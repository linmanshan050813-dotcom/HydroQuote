"""Human-in-the-loop helpers for LangGraph interrupt/resume."""

from __future__ import annotations

from typing import Any


def needs_technical_gate(state: dict[str, Any]) -> bool:
    pkg = state.get("technical_package") or {}
    if pkg.get("technical_approval_required"):
        return True
    if pkg.get("readiness") == "needs_human_review":
        return True
    hr = state.get("human_review") or {}
    return bool(hr.get("technical_pending"))


def needs_price_gate(state: dict[str, Any]) -> bool:
    cost = state.get("cost_breakdown") or {}
    return bool(cost.get("review_required"))


def apply_review_decision(state: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    """Merge authorized review payload into state (caller must verify auth)."""
    decision = (review or {}).get("decision")
    hr = dict(state.get("human_review") or {})
    hr["last_decision"] = decision
    hr["rule_version"] = review.get("rule_version")
    hr["reviewer_id"] = review.get("reviewer_id")
    out = dict(state)
    out["human_review"] = hr
    if decision == "approve":
        # Allow firm path only when reviewer supplies approved risk rate if needed
        inquiry = dict(out.get("inquiry") or {})
        if review.get("risk_reserve_rate") is not None:
            inquiry["risk_reserve_rate"] = review["risk_reserve_rate"]
            inquiry["risk_reserve_rate_approved"] = True
            out["inquiry"] = inquiry
        cost = dict(out.get("cost_breakdown") or {})
        if review.get("override_review_required") is True:
            cost["review_required"] = False
            out["cost_breakdown"] = cost
        out["status"] = "preliminary"
    elif decision == "reject":
        out["status"] = "rejected"
    else:
        out["status"] = "review_required"
    return out
