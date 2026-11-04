"""Five equipment cost functions executed in parallel (asyncio.gather)."""

from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Any

from hydroquote.contracts.models import InquiryData, TechnicalSelectionPackage
from hydroquote.domain.pricing import PricingEngine


async def _run_sync(fn, *args):
    return await asyncio.to_thread(fn, *args)


async def parallel_equipment_costs(
    engine: PricingEngine,
    inquiry: InquiryData,
    technical: TechnicalSelectionPackage,
) -> dict[str, Any]:
    unit_kw = Decimal(str(technical.unit_capacity_kw))
    qty = int(technical.unit_count)
    turbine_type = technical.recommended_turbine_type
    level = inquiry.automation_level or "Standard"

    results = await asyncio.gather(
        _run_sync(engine.cost_hydro_turbine, unit_kw, qty, turbine_type),
        _run_sync(
            engine.cost_generator_avr,
            unit_kw,
            qty,
            inquiry.frequency_hz,
            inquiry.voltage_factor,
            inquiry.speed_factor,
        ),
        _run_sync(engine.cost_speed_governor, unit_kw, qty, level),
        _run_sync(engine.cost_inlet_valve, unit_kw, qty, inquiry.pressure_factor, None),
        _run_sync(engine.cost_automation_system, qty, level, False),
    )
    keys = [
        "hydro_turbine",
        "generator_avr",
        "speed_governor",
        "inlet_valve",
        "automation_system",
    ]
    return {k: r.model_dump(mode="json") for k, r in zip(keys, results)}
