"""Fast Quote deterministic technical selection."""

from __future__ import annotations

from decimal import Decimal

from hydroquote.contracts.models import (
    EquipmentScopeItem,
    InquiryData,
    TechnicalSelectionPackage,
)
from hydroquote.domain.hydraulic import check_hydraulic, suggest_turbine_type


def build_fast_technical_package(inquiry: InquiryData) -> TechnicalSelectionPackage:
    if inquiry.net_head_m is None:
        raise ValueError("net_head_required")
    units = inquiry.number_of_units or 1
    unit_kw = inquiry.unit_capacity_kw
    if unit_kw is None and inquiry.installed_capacity_kw:
        unit_kw = inquiry.installed_capacity_kw / units
    if unit_kw is None:
        raise ValueError("unit_capacity_required")

    turbine = inquiry.turbine_type or suggest_turbine_type(
        inquiry.net_head_m, inquiry.flow_variability
    )
    hydro = check_hydraulic(inquiry)
    if hydro.get("notes") and "hydraulic_power_vs_installed_conflict" in hydro["notes"]:
        # Mark conflict on inquiry path via readiness
        pass

    scope = [
        EquipmentScopeItem(code="hydro_turbine", name="Hydro Turbine", quantity=units),
        EquipmentScopeItem(
            code="generator_avr", name="Generator and Exciter / AVR", quantity=units
        ),
        EquipmentScopeItem(code="speed_governor", name="Speed Governor", quantity=units),
        EquipmentScopeItem(code="inlet_valve", name="Inlet Valve", quantity=units),
        EquipmentScopeItem(
            code="automation_system",
            name="Automation System",
            quantity=units,
            notes="Standard PLC Automation (default)",
        ),
    ]
    optional: list[str] = []
    if inquiry.automation_level == "Advanced":
        optional.append("Advanced SCADA / remote monitoring (optional upgrade)")

    readiness = "firm_ready"
    approval = False
    if hydro.get("review_required") or hydro.get("efficiency_assumed"):
        readiness = "preliminary_ready"
        approval = True
    if hydro.get("consistent") is False:
        readiness = "needs_human_review"
        approval = True

    return TechnicalSelectionPackage(
        recommended_turbine_type=turbine,
        unit_count=units,
        unit_capacity_kw=Decimal(str(unit_kw)),
        hydraulic_calculation=hydro,
        equipment_scope=scope,
        automation_scope=f"{inquiry.automation_level} PLC Automation",
        optional_upgrades=optional,
        assumptions=[
            a for a in [f"efficiency_assumed" if hydro.get("efficiency_assumed") else None] if a
        ],
        risk_notes=list(hydro.get("notes") or []),
        technical_approval_required=approval,
        readiness=readiness,  # type: ignore[arg-type]
        source_provenance=["fast_quote_rules", "pricing_rules.yaml"],
        selection_path="fast_quote",
    )
