"""Single public MCP tool: hydroquote_quote."""

from __future__ import annotations

import os
from typing import Any, Optional

try:
    from mcp.server.mcpserver import MCPServer as _MCP
except ImportError:  # mcp<2
    from mcp.server.fastmcp import FastMCP as _MCP  # type: ignore

from hydroquote.application.quotation_service import QuotationApplication

_app_service: QuotationApplication | None = None


def get_service() -> QuotationApplication:
    global _app_service
    if _app_service is None:
        _app_service = QuotationApplication()
    return _app_service


def set_service(service: QuotationApplication) -> None:
    global _app_service
    _app_service = service


def _tenant_from_auth(auth_token: Optional[str]) -> tuple[str, str]:
    """
    Map bearer/token to tenant_id and role.
    MVP: HYDROQUOTE_TOKENS=token:tenant:role,token2:tenant2:role
    """
    raw = os.getenv("HYDROQUOTE_TOKENS", "devtoken:tenant-demo:customer")
    mapping = {}
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        bits = part.split(":")
        if len(bits) >= 3:
            mapping[bits[0]] = (bits[1], bits[2])
    token = auth_token or os.getenv("HYDROQUOTE_DEFAULT_TOKEN", "devtoken")
    if token not in mapping:
        raise PermissionError("unauthorized")
    return mapping[token]


def create_mcp_server(service: QuotationApplication | None = None):
    if service is not None:
        set_service(service)
    mcp = _MCP("HydroQuote")

    @mcp.tool()
    async def hydroquote_quote(
        schema_version: str = "1.0",
        operation: str = "create",
        request_id: str = "",
        quote_id: str | None = None,
        project_text: str | None = None,
        parameters: dict | None = None,
        revisions: dict | None = None,
        include_pi: bool = False,
        review: dict | None = None,
        auth_token: str | None = None,
    ) -> dict:
        """HydroQuote unified quotation tool (create/revise/get/submit_review)."""
        if schema_version != "1.0":
            return {"status": "error", "error": "unsupported_schema_version"}
        if not request_id and operation != "get":
            return {"status": "error", "error": "request_id_required"}
        try:
            tenant_id, role = _tenant_from_auth(auth_token)
        except PermissionError:
            return {"status": "error", "error": "unauthorized"}

        svc = get_service()
        try:
            if operation == "create":
                return await svc.create(
                    tenant_id=tenant_id,
                    request_id=request_id,
                    project_text=project_text,
                    parameters=parameters,
                    include_pi=include_pi,
                )
            if operation == "revise":
                if not quote_id:
                    return {"status": "error", "error": "quote_id_required"}
                return await svc.revise(
                    tenant_id=tenant_id,
                    request_id=request_id or f"revise-{quote_id}",
                    quote_id=quote_id,
                    revisions=revisions,
                    project_text=project_text,
                    include_pi=include_pi,
                )
            if operation == "get":
                if not quote_id:
                    return {"status": "error", "error": "quote_id_required"}
                # Swarm role via special token role=swarm
                view_role = "swarm" if role == "swarm" else ("reviewer" if role in ("reviewer", "admin") else "customer")
                return svc.get(
                    tenant_id=tenant_id,
                    quote_id=quote_id,
                    role=view_role,
                    include_pi=include_pi,
                )
            if operation == "submit_review":
                if not quote_id:
                    return {"status": "error", "error": "quote_id_required"}
                return await svc.submit_review(
                    tenant_id=tenant_id,
                    quote_id=quote_id,
                    review=review or {},
                    reviewer_role=role,
                )
            return {"status": "error", "error": "unknown_operation"}
        except PermissionError as exc:
            return {"status": "error", "error": str(exc)}
        except KeyError:
            return {"status": "error", "error": "quote_not_found"}
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "error": f"internal:{type(exc).__name__}"}

    return mcp


def get_mcp_app(service: QuotationApplication | None = None):
    """Return ASGI app for Streamable HTTP mount when supported."""
    mcp = create_mcp_server(service)
    # FastMCP exposes streamable HTTP ASGI in recent SDK versions
    if hasattr(mcp, "streamable_http_app"):
        return mcp.streamable_http_app()
    if hasattr(mcp, "sse_app"):
        return mcp.sse_app()
    return mcp
