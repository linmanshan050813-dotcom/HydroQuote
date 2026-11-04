import asyncio

from hydroquote.orchestration.graph import build_hydroquote_graph, run_quotation_graph
from hydroquote.swarm.adapter import SwarmAdapter


def test_expert_route_swarm_unavailable_review_required():
    """Complex project must NOT silently fall back to Fast Quote."""
    graph = build_hydroquote_graph(swarm_adapter=SwarmAdapter(enabled=False))

    async def _run():
        return await run_quotation_graph(
            graph,
            quote_id="Q-TEST-EXP",
            request_id="req-exp-1",
            tenant_id="tenant-demo",
            inquiry={
                "net_head_m": 50,
                "design_flow_m3s": 6,
                "installed_capacity_kw": 2400,
                "number_of_units": 2,
                "unit_capacity_kw": 1200,
                "turbine_type": "Francis",
                "sediment_load": "high",
                "frequency_hz": 50,
            },
            confirmed=True,
        )

    result = asyncio.run(_run())
    assert result.get("routing_path") == "expert_quote"
    assert result.get("swarm_called") is True
    assert result.get("status") == "review_required"
    # Must not invent a Fast technical package
    assert not result.get("technical_package")
    events = [t["event"] for t in result.get("trace") or []]
    assert "expert_quote_failed" in events
