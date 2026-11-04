"""Golden pricing cases from 报价规则.docx."""

from decimal import Decimal

from hydroquote.contracts.models import InquiryData
from hydroquote.domain.pricing import PricingEngine
from hydroquote.domain.selection import build_fast_technical_package


def test_francis_2x1200_turbine_base_108000():
    engine = PricingEngine()
    line = engine.cost_hydro_turbine(Decimal("1200"), 2, "Francis")
    assert line.line_total == Decimal("108000.00")
    assert line.unit_base_price == Decimal("54000.00")
    assert not line.review_required


def test_generator_1200_base():
    engine = PricingEngine()
    line = engine.cost_generator_avr(Decimal("1200"), 2, frequency_hz=50)
    # 82400 * 2 = 164800
    assert line.unit_base_price == Decimal("82400.00")
    assert line.line_total == Decimal("164800.00")


def test_personnel_formula_not_table_3000():
    engine = PricingEngine()
    # Discrepancy D1: 1500 kW total must be 30000 via formula, not 3000
    assert engine.personnel_cost(Decimal("1500")) == Decimal("30000.00")


def test_risk_unapproved_blocks_commercial():
    engine = PricingEngine()
    inquiry = InquiryData(
        net_head_m=50,
        design_flow_m3s=6,
        installed_capacity_kw=2400,
        number_of_units=2,
        unit_capacity_kw=1200,
        turbine_type="Francis",
        frequency_hz=50,
        risk_reserve_rate_approved=False,
    )
    tech = build_fast_technical_package(inquiry)
    bd = engine.compute_breakdown(inquiry, tech)
    assert bd.review_required
    assert "risk_reserve_rate_unapproved" in bd.review_reasons
    assert bd.commercial_quotation is None
    # Turbine portion still deterministic
    assert bd.equipment_costs["hydro_turbine"].line_total == Decimal("108000.00")


def test_commercial_multiplier_with_approved_risk():
    engine = PricingEngine()
    inquiry = InquiryData(
        net_head_m=50,
        design_flow_m3s=6,
        installed_capacity_kw=2400,
        number_of_units=2,
        unit_capacity_kw=1200,
        turbine_type="Francis",
        frequency_hz=50,
        automation_level="Standard",
        risk_reserve_rate=Decimal("0.05"),
        risk_reserve_rate_approved=True,
    )
    tech = build_fast_technical_package(inquiry)
    bd = engine.compute_breakdown(inquiry, tech)
    assert not bd.review_required
    assert bd.internal_cost is not None
    assert bd.commercial_quotation == (bd.internal_cost * Decimal("2.40")).quantize(
        Decimal("0.01")
    )


def test_idempotent_same_inputs():
    engine = PricingEngine()
    inquiry = InquiryData(
        net_head_m=50,
        design_flow_m3s=6,
        installed_capacity_kw=2400,
        number_of_units=2,
        unit_capacity_kw=1200,
        turbine_type="Francis",
        frequency_hz=50,
        risk_reserve_rate=Decimal("0.05"),
        risk_reserve_rate_approved=True,
    )
    tech = build_fast_technical_package(inquiry)
    a = engine.compute_breakdown(inquiry, tech)
    b = engine.compute_breakdown(inquiry, tech)
    assert a.commercial_quotation == b.commercial_quotation
    assert a.calculation_idempotency_key == b.calculation_idempotency_key


def test_over_5000kw_review():
    engine = PricingEngine()
    line = engine.cost_hydro_turbine(Decimal("6000"), 1, "Francis")
    assert line.review_required
