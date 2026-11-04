import asyncio
from decimal import Decimal

from hydroquote.contracts.models import InquiryData
from hydroquote.domain.pricing import PricingEngine
from hydroquote.domain.selection import build_fast_technical_package
from hydroquote.orchestration.cost_fanout import parallel_equipment_costs


def test_five_parallel_keys():
    engine = PricingEngine()
    inquiry = InquiryData(
        net_head_m=50,
        design_flow_m3s=6,
        installed_capacity_kw=2400,
        number_of_units=2,
        unit_capacity_kw=1200,
        turbine_type="Francis",
        frequency_hz=50,
    )
    tech = build_fast_technical_package(inquiry)
    result = asyncio.run(parallel_equipment_costs(engine, inquiry, tech))
    assert set(result.keys()) == {
        "hydro_turbine",
        "generator_avr",
        "speed_governor",
        "inlet_valve",
        "automation_system",
    }
    assert Decimal(result["hydro_turbine"]["line_total"]) == Decimal("108000.00")
