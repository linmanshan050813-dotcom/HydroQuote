import asyncio
import os

from hydroquote.application.quotation_service import QuotationApplication
from hydroquote.application.quote_store import QuoteStore
from hydroquote.mcp.server import create_mcp_server, set_service
from pathlib import Path


def test_mcp_tool_create_and_list():
    os.environ["HYDROQUOTE_TOKENS"] = "devtoken:tenant-demo:customer,revtoken:tenant-demo:reviewer"
    store = QuoteStore(Path("data") / "quotes_test_mcp")
    svc = QuotationApplication(store=store)
    set_service(svc)
    mcp = create_mcp_server(svc)
    tools = asyncio.run(mcp.list_tools())
    names = [t.name for t in tools]
    assert names == ["hydroquote_quote"]

    async def _call():
        return await svc.create(
            tenant_id="tenant-demo",
            request_id="mcp-contract-1",
            parameters={
                "net_head_m": 50,
                "design_flow_m3s": 6,
                "installed_capacity_kw": 2400,
                "number_of_units": 2,
                "unit_capacity_kw": 1200,
                "turbine_type": "Francis",
                "frequency_hz": 50,
                "risk_reserve_rate": "0.05",
                "risk_reserve_rate_approved": True,
            },
        )

    result = asyncio.run(_call())
    assert result["quote_id"]
    assert result.get("workflow_path") == "fast_quote" or (
        result.get("data", {}).get("routing_path") == "fast_quote"
    )
    # Prefer top-level workflow_path once persist succeeds
    assert result.get("workflow_path") == "fast_quote"
    assert "internal_cost" not in result
    assert "risk_reserve_rate" not in result


def test_unauthorized_review():
    os.environ["HYDROQUOTE_TOKENS"] = "devtoken:tenant-demo:customer"
    store = QuoteStore(Path("data") / "quotes_test_mcp2")
    svc = QuotationApplication(store=store)

    async def _run():
        created = await svc.create(
            tenant_id="tenant-demo",
            request_id="mcp-contract-2",
            parameters={
                "net_head_m": 50,
                "design_flow_m3s": 6,
                "installed_capacity_kw": 2400,
                "number_of_units": 2,
                "unit_capacity_kw": 1200,
                "turbine_type": "Francis",
            },
        )
        try:
            await svc.submit_review(
                tenant_id="tenant-demo",
                quote_id=created["quote_id"],
                review={"decision": "approve", "risk_reserve_rate": "0.05"},
                reviewer_role="customer",
            )
            return False
        except PermissionError:
            return True

    assert asyncio.run(_run()) is True
