"""Deterministic Decimal pricing engine — sole authority for money."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Optional

import yaml

from hydroquote.contracts.models import (
    MAIN_EQUIPMENT_KEYS,
    CostBreakdown,
    EquipmentCostLine,
    InquiryData,
    TechnicalSelectionPackage,
)

TWOPLACES = Decimal("0.01")
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RULES = ROOT / "config" / "pricing_rules.yaml"


def D(v: Any) -> Decimal:
    return Decimal(str(v))


def money(v: Decimal) -> Decimal:
    return v.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def load_pricing_rules(path: Path | None = None) -> dict[str, Any]:
    p = path or DEFAULT_RULES
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f)


class PricingEngine:
    def __init__(self, rules: dict[str, Any] | None = None):
        self.rules = rules or load_pricing_rules()
        self.rule_version = str(self.rules.get("version", "unknown"))

    def _type_factor(self, turbine_type: str) -> Decimal:
        factors = self.rules.get("turbine_type_factors", {})
        if turbine_type not in factors:
            raise ValueError(f"unknown_turbine_type:{turbine_type}")
        return D(factors[turbine_type])

    def _freq_factor(self, frequency_hz: Optional[float]) -> Decimal:
        if frequency_hz is None:
            return D(self.rules["defaults"]["frequency_factors"]["50"])
        key = str(int(frequency_hz))
        ff = self.rules["defaults"]["frequency_factors"]
        if key not in ff:
            raise ValueError(f"unsupported_frequency:{frequency_hz}")
        return D(ff[key])

    def turbine_unit_base(self, unit_kw: Decimal) -> tuple[Decimal, bool, list[str]]:
        """Return (base_price_per_unit, review_required, reasons)."""
        reasons: list[str] = []
        if unit_kw > D(5000):
            return D(0), True, [">5000kW_manual_review"]
        if unit_kw <= D(500):
            return max(D(30000), unit_kw * D(50)), False, []
        if unit_kw <= D(1000):
            return money(unit_kw * D(50)), False, []
        if unit_kw <= D(1500):
            # Exact: 50000 + (Cap - 1000) * 20
            return money(D(50000) + (unit_kw - D(1000)) * D(20)), False, []
        if unit_kw <= D(3000):
            # Band 38–40 $/kW — no approved single coefficient
            return D(0), True, ["turbine_1500_3000_price_band_unapproved"]
        if unit_kw <= D(5000):
            return D(0), True, ["turbine_3000_5000_price_band_unapproved"]
        return D(0), True, [">5000kW_manual_review"]

    def generator_unit_base(self, unit_kw: Decimal) -> tuple[Decimal, bool, list[str]]:
        if unit_kw > D(5000):
            return D(0), True, [">5000kW_manual_review"]
        if unit_kw <= D(500):
            return max(D(40000), unit_kw * D(75)), False, []
        if unit_kw <= D(1000):
            return money(unit_kw * D(75)), False, []
        if unit_kw <= D(1500):
            return money(D(75000) + (unit_kw - D(1000)) * D(37)), False, []
        if unit_kw <= D(3000):
            return D(0), True, ["generator_1500_3000_price_band_unapproved"]
        if unit_kw <= D(5000):
            return D(0), True, ["generator_3000_5000_price_band_unapproved"]
        return D(0), True, [">5000kW_manual_review"]

    def governor_unit_base(self, unit_kw: Decimal) -> tuple[Decimal, bool, list[str]]:
        if unit_kw > D(5000):
            return D(0), True, [">5000kW_manual_review"]
        if unit_kw <= D(1000):
            return D(13500), False, []
        if unit_kw <= D(1500):
            return money(D(13500) + (unit_kw - D(1000)) * D(3)), False, []
        return D(0), True, ["governor_outside_exact_interpolation"]

    def valve_unit_base(self, unit_kw: Decimal) -> tuple[Decimal, bool, list[str]]:
        if unit_kw > D(5000):
            return D(0), True, [">5000kW_manual_review"]
        if unit_kw <= D(1000):
            return D(11800), False, []
        if unit_kw <= D(1500):
            return money(D(11800) + (unit_kw - D(1000)) * D("13.4")), False, []
        return D(0), True, ["valve_outside_exact_interpolation"]

    def automation_unit_base(self, level: str) -> tuple[Decimal, bool, list[str]]:
        bases = self.rules.get("automation_system_base", {})
        if level not in bases:
            return D(0), True, [f"unknown_automation_level:{level}"]
        return D(bases[level]), False, []

    def cost_hydro_turbine(
        self,
        unit_kw: Decimal,
        quantity: int,
        turbine_type: str,
    ) -> EquipmentCostLine:
        base, rev, reasons = self.turbine_unit_base(unit_kw)
        tf = self._type_factor(turbine_type)
        total = money(base * tf * D(quantity)) if not rev else D(0)
        return EquipmentCostLine(
            equipment_key="hydro_turbine",
            display_name="Hydro Turbine",
            unit_base_price=base,
            quantity=quantity,
            factors={"turbine_type_factor": str(tf)},
            line_total=total,
            review_required=rev,
            review_reasons=reasons,
            rule_version=self.rule_version,
        )

    def cost_generator_avr(
        self,
        unit_kw: Decimal,
        quantity: int,
        frequency_hz: Optional[float] = 50.0,
        voltage_factor: Optional[Decimal] = None,
        speed_factor: Optional[Decimal] = None,
    ) -> EquipmentCostLine:
        base, rev, reasons = self.generator_unit_base(unit_kw)
        ff = self._freq_factor(frequency_hz)
        vf = voltage_factor if voltage_factor is not None else D(self.rules["defaults"]["voltage_factor"])
        sf = speed_factor if speed_factor is not None else D(self.rules["defaults"]["speed_factor"])
        total = money(base * vf * ff * sf * D(quantity)) if not rev else D(0)
        return EquipmentCostLine(
            equipment_key="generator_avr",
            display_name="Generator and Exciter / AVR",
            unit_base_price=base,
            quantity=quantity,
            factors={
                "voltage_factor": str(vf),
                "frequency_factor": str(ff),
                "speed_factor": str(sf),
            },
            line_total=total,
            review_required=rev,
            review_reasons=reasons,
            rule_version=self.rule_version,
        )

    def cost_speed_governor(
        self,
        unit_kw: Decimal,
        quantity: int,
        automation_level: str = "Standard",
    ) -> EquipmentCostLine:
        base, rev, reasons = self.governor_unit_base(unit_kw)
        af_map = self.rules.get("automation_governor_factors", {})
        if automation_level not in af_map:
            rev = True
            reasons = reasons + [f"unknown_automation_level:{automation_level}"]
            af = D(1)
        else:
            af = D(af_map[automation_level])
        total = money(base * af * D(quantity)) if not rev else D(0)
        return EquipmentCostLine(
            equipment_key="speed_governor",
            display_name="Speed Governor",
            unit_base_price=base,
            quantity=quantity,
            factors={"automation_factor": str(af)},
            line_total=total,
            review_required=rev,
            review_reasons=reasons,
            rule_version=self.rule_version,
        )

    def cost_inlet_valve(
        self,
        unit_kw: Decimal,
        quantity: int,
        pressure_factor: Optional[Decimal] = None,
        accessory_factor: Optional[Decimal] = None,
    ) -> EquipmentCostLine:
        base, rev, reasons = self.valve_unit_base(unit_kw)
        pf = pressure_factor if pressure_factor is not None else D(self.rules["defaults"]["pressure_factor"])
        af = accessory_factor if accessory_factor is not None else D(self.rules["defaults"]["accessory_factor"])
        total = money(base * pf * af * D(quantity)) if not rev else D(0)
        return EquipmentCostLine(
            equipment_key="inlet_valve",
            display_name="Inlet Valve",
            unit_base_price=base,
            quantity=quantity,
            factors={"pressure_factor": str(pf), "accessory_factor": str(af)},
            line_total=total,
            review_required=rev,
            review_reasons=reasons,
            rule_version=self.rule_version,
        )

    def cost_automation_system(
        self,
        quantity: int,
        automation_level: str = "Standard",
        plant_level: bool = False,
    ) -> EquipmentCostLine:
        base, rev, reasons = self.automation_unit_base(automation_level)
        # Plant-level: do not linearize by unit count for Advanced full plant — use qty=1
        qty = 1 if plant_level else quantity
        total = money(base * D(qty)) if not rev else D(0)
        return EquipmentCostLine(
            equipment_key="automation_system",
            display_name="Automation System",
            unit_base_price=base,
            quantity=qty,
            factors={"automation_level": automation_level, "plant_level": str(plant_level)},
            line_total=total,
            review_required=rev,
            review_reasons=reasons,
            rule_version=self.rule_version,
        )

    def personnel_cost(self, total_capacity_kw: Decimal) -> Decimal:
        # Formula wins over erroneous 1500kW=3000 table (discrepancy D1)
        rate = D(self.rules["personnel_cost_per_1000kw"])
        return money(rate * total_capacity_kw / D(1000))

    def compute_breakdown(
        self,
        inquiry: InquiryData,
        technical: TechnicalSelectionPackage,
        revision: str = "1",
    ) -> CostBreakdown:
        unit_kw = D(technical.unit_capacity_kw)
        qty = int(technical.unit_count)
        turbine_type = technical.recommended_turbine_type
        level = inquiry.automation_level or "Standard"

        lines = {
            "hydro_turbine": self.cost_hydro_turbine(unit_kw, qty, turbine_type),
            "generator_avr": self.cost_generator_avr(
                unit_kw,
                qty,
                inquiry.frequency_hz,
                inquiry.voltage_factor,
                inquiry.speed_factor,
            ),
            "speed_governor": self.cost_speed_governor(unit_kw, qty, level),
            "inlet_valve": self.cost_inlet_valve(unit_kw, qty, inquiry.pressure_factor),
            "automation_system": self.cost_automation_system(qty, level),
        }
        assert set(lines.keys()) == set(MAIN_EQUIPMENT_KEYS)

        review_reasons: list[str] = []
        review = False
        for line in lines.values():
            if line.review_required:
                review = True
                review_reasons.extend(line.review_reasons)

        main = money(sum((ln.line_total for ln in lines.values()), D(0)))
        total_cap = unit_kw * D(qty)
        personnel = self.personnel_cost(total_cap)
        additional = personnel  # personnel stands for project additional bundle per rules

        after_sales = D(self.rules["after_sales_rate"])
        risk: Optional[Decimal] = None
        internal: Optional[Decimal] = None
        commercial: Optional[Decimal] = None

        if not inquiry.risk_reserve_rate_approved or inquiry.risk_reserve_rate is None:
            review = True
            review_reasons.append("risk_reserve_rate_unapproved")
        else:
            risk = D(inquiry.risk_reserve_rate)
            if not review:
                internal = money((main + additional) * (D(1) + risk + after_sales))
                commercial = money(internal * D(self.rules["commercial_multiplier"]))

        # Even if risk approved, equipment review blocks firm commercial
        if review:
            internal = None
            commercial = None

        idem = f"{turbine_type}:{unit_kw}:{qty}:{self.rule_version}:{revision}"
        return CostBreakdown(
            equipment_costs=lines,
            main_equipment_base_cost=main,
            project_additional_cost=additional,
            personnel_cost=personnel,
            risk_reserve_rate=risk,
            after_sales_rate=after_sales,
            internal_cost=internal,
            commercial_quotation=commercial,
            review_required=review,
            review_reasons=sorted(set(review_reasons)),
            rule_version=self.rule_version,
            calculation_idempotency_key=idem,
        )
