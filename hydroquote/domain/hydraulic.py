"""Hydraulic power check: P = 9.81 * Q * H * eta."""

from __future__ import annotations

from typing import Any, Optional

from hydroquote.contracts.models import InquiryData


def hydraulic_power_kw(
    design_flow_m3s: float,
    net_head_m: float,
    efficiency: float,
) -> float:
    return 9.81 * design_flow_m3s * net_head_m * efficiency


def check_hydraulic(inquiry: InquiryData, default_eta: float = 0.88) -> dict[str, Any]:
    result: dict[str, Any] = {
        "formula": "P_kW = 9.81 * Q * H * eta",
        "efficiency_used": None,
        "efficiency_assumed": False,
        "calculated_power_kw": None,
        "installed_capacity_kw": inquiry.installed_capacity_kw,
        "consistent": None,
        "notes": [],
        "review_required": False,
    }
    if inquiry.net_head_m is None or inquiry.design_flow_m3s is None:
        result["notes"].append("missing_head_or_flow")
        result["review_required"] = True
        return result

    eta = inquiry.efficiency
    if eta is None:
        eta = default_eta
        result["efficiency_assumed"] = True
        result["notes"].append(f"efficiency_assumed_{default_eta}")
        result["review_required"] = True  # assumption affects firm readiness
    result["efficiency_used"] = eta
    p = hydraulic_power_kw(inquiry.design_flow_m3s, inquiry.net_head_m, eta)
    result["calculated_power_kw"] = round(p, 3)

    if inquiry.installed_capacity_kw is not None:
        # Allow ~15% band for plant losses / selection margin
        ratio = inquiry.installed_capacity_kw / p if p else 0
        consistent = 0.7 <= ratio <= 1.25
        result["consistent"] = consistent
        if not consistent:
            result["notes"].append("hydraulic_power_vs_installed_conflict")
            result["review_required"] = True
    return result


def suggest_turbine_type(net_head_m: float, flow_variability: Optional[str] = None) -> str:
    """Simple rule-based type suggestion for Fast Quote."""
    if net_head_m < 20:
        return "Kaplan" if flow_variability in ("seasonal", "high", "extreme") else "Tubular"
    if net_head_m < 50:
        return "Francis"
    if net_head_m < 300:
        return "Francis"
    return "Pelton"
