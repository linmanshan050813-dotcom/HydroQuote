import asyncio

from hydroquote.orchestration.graph import build_hydroquote_graph, run_quotation_graph
from hydroquote.swarm.adapter import SwarmAdapter


def test_fast_quote_no_swarm():
    graph = build_hydroquote_graph(swarm_adapter=SwarmAdapter(enabled=False))

    async def _run():
        return await run_quotation_graph(
            graph,
            quote_id="Q-TEST-FAST",
            request_id="req-fast-1",
            tenant_id="tenant-demo",
            project_text="",
            inquiry={
                "net_head_m": 50,
                "design_flow_m3s": 6,
                "installed_capacity_kw": 2400,
                "number_of_units": 2,
                "unit_capacity_kw": 1200,
                "turbine_type": "Francis",
                "frequency_hz": 50,
                "automation_level": "Standard",
                "risk_reserve_rate": "0.05",
                "risk_reserve_rate_approved": True,
            },
            confirmed=True,
        )

    result = asyncio.run(_run())
    assert result.get("routing_path") == "fast_quote"
    assert result.get("swarm_called") is False
    assert result.get("technical_package")
    assert result.get("equipment_costs")
    events = [t["event"] for t in result.get("trace") or []]
    assert "fast_quote" in events
    assert "engineering_cost_parallel" in events


def test_needs_input_no_swarm():
    graph = build_hydroquote_graph(swarm_adapter=SwarmAdapter(enabled=False))

    async def _run():
        return await run_quotation_graph(
            graph,
            quote_id="Q-TEST-MISS",
            request_id="req-miss-1",
            tenant_id="tenant-demo",
            project_text="Need a 2MW plant",
            inquiry={"installed_capacity_kw": 2000},
            confirmed=False,
        )

    result = asyncio.run(_run())
    assert result.get("status") == "needs_input"
    assert result.get("swarm_called") is False
    assert not result.get("technical_package")
