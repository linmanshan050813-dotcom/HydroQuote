"""Quotation description agent — never alters cost numbers."""

from __future__ import annotations

from typing import Any


class QuotationAgentAdapter:
    async def describe(self, cost_breakdown: dict[str, Any], technical: dict[str, Any]) -> str:
        turbine = technical.get("recommended_turbine_type")
        units = technical.get("unit_count")
        unit_kw = technical.get("unit_capacity_kw")
        commercial = cost_breakdown.get("commercial_quotation")
        review = cost_breakdown.get("review_required")
        if review:
            return (
                f"Technical selection: {units}×{unit_kw} kW {turbine}. "
                "Commercial quotation pending human review of pricing rules / risk reserve."
            )
        return (
            f"Technical selection: {units}×{unit_kw} kW {turbine}. "
            f"Commercial quotation USD {commercial} (InternalCost × 2.40; "
            f"rule {cost_breakdown.get('rule_version')})."
        )
