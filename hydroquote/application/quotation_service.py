"""Shared application service for FastAPI + MCP."""

from __future__ import annotations

import base64
from typing import Any, Optional

from hydroquote.application.quote_store import QuoteStore
from hydroquote.contracts.models import InquiryData, QuotationStatus
from hydroquote.domain.inquiry import missing_required_fields, normalize_units_config
from hydroquote.domain.pi import build_pi_document
from hydroquote.domain.pricing import PricingEngine
from hydroquote.orchestration.approval import apply_review_decision
from hydroquote.orchestration.graph import build_hydroquote_graph, run_quotation_graph
from hydroquote.swarm.adapter import SwarmAdapter


INTERNAL_COST_KEYS = {
    "internal_cost",
    "MainEquipmentBaseCost",
    "main_equipment_base_cost",
    "risk_reserve_rate",
    "RiskReserveRate",
    "personnel_cost",
    "project_additional_cost",
}


class QuotationApplication:
    def __init__(
        self,
        store: QuoteStore | None = None,
        swarm: SwarmAdapter | None = None,
    ):
        self.store = store or QuoteStore()
        self.swarm = swarm or SwarmAdapter()
        self.engine = PricingEngine()
        self.graph = build_hydroquote_graph(swarm_adapter=self.swarm, pricing_engine=self.engine)
        self._pi_cache: dict[str, bytes] = {}

    async def create(
        self,
        *,
        tenant_id: str,
        request_id: str,
        project_text: str | None = None,
        parameters: dict[str, Any] | None = None,
        pi_fields: dict[str, Any] | None = None,
        include_pi: bool = False,
    ) -> dict[str, Any]:
        existing = self.store.find_by_request_id(tenant_id, request_id)
        if existing:
            return self.public_view(existing, role="customer", include_pi=include_pi)

        inquiry_dict: dict[str, Any] = {}
        if parameters:
            inquiry_dict = InquiryData.model_validate(parameters).model_dump(mode="json")
        confirmed = False
        if inquiry_dict:
            norm = normalize_units_config(InquiryData.model_validate(inquiry_dict))
            inquiry_dict = norm.model_dump(mode="json")
            confirmed = len(missing_required_fields(norm)) == 0

        record = self.store.create(
            tenant_id=tenant_id,
            request_id=request_id,
            payload={
                "status": QuotationStatus.PROCESSING.value,
                "workflow_stage": "customer_inquiry",
            },
        )
        quote_id = record["quote_id"]
        result = await run_quotation_graph(
            self.graph,
            quote_id=quote_id,
            request_id=request_id,
            tenant_id=tenant_id,
            project_text=project_text or "",
            inquiry=inquiry_dict,
            confirmed=confirmed,
            pi_fields=pi_fields,
            thread_id=quote_id,
        )
        self._persist_graph_result(quote_id, tenant_id, result, include_pi=include_pi)
        updated = self.store.get(quote_id, tenant_id)
        assert updated
        return self.public_view(updated, role="customer", include_pi=include_pi)

    async def revise(
        self,
        *,
        tenant_id: str,
        request_id: str,
        quote_id: str,
        revisions: dict[str, Any] | None = None,
        project_text: str | None = None,
        include_pi: bool = False,
    ) -> dict[str, Any]:
        record = self.store.get(quote_id, tenant_id)
        if not record:
            raise KeyError("quote_not_found")
        data = dict(record.get("data") or {})
        inquiry = dict(data.get("inquiry") or {})
        revisions = revisions or {}
        inquiry.update({k: v for k, v in revisions.items() if v is not None})
        pi_fields = dict(data.get("pi_fields") or {})
        if "pi_fields" in revisions and isinstance(revisions["pi_fields"], dict):
            pi_fields.update(revisions["pi_fields"])
        norm = normalize_units_config(InquiryData.model_validate(inquiry))
        confirmed = len(missing_required_fields(norm)) == 0
        result = await run_quotation_graph(
            self.graph,
            quote_id=quote_id,
            request_id=request_id,
            tenant_id=tenant_id,
            project_text=project_text or data.get("project_text") or "",
            inquiry=norm.model_dump(mode="json"),
            confirmed=confirmed,
            pi_fields=pi_fields,
            thread_id=quote_id,
        )
        self._persist_graph_result(quote_id, tenant_id, result, include_pi=include_pi)
        updated = self.store.get(quote_id, tenant_id)
        assert updated
        return self.public_view(updated, role="customer", include_pi=include_pi)

    def get(
        self,
        *,
        tenant_id: str,
        quote_id: str,
        role: str = "customer",
        include_pi: bool = False,
    ) -> dict[str, Any]:
        record = self.store.get(quote_id, tenant_id)
        if not record:
            raise KeyError("quote_not_found")
        return self.public_view(record, role=role, include_pi=include_pi)

    async def submit_review(
        self,
        *,
        tenant_id: str,
        quote_id: str,
        review: dict[str, Any],
        reviewer_role: str,
    ) -> dict[str, Any]:
        if reviewer_role not in ("reviewer", "admin"):
            raise PermissionError("review_write_denied")
        record = self.store.get(quote_id, tenant_id)
        if not record:
            raise KeyError("quote_not_found")
        data = dict(record.get("data") or {})
        merged = apply_review_decision(data, review)
        # Re-run costing if approved with risk rate
        if review.get("decision") == "approve":
            result = await run_quotation_graph(
                self.graph,
                quote_id=quote_id,
                request_id=record["request_id"],
                tenant_id=tenant_id,
                project_text=data.get("project_text") or "",
                inquiry=merged.get("inquiry") or {},
                confirmed=True,
                pi_fields=data.get("pi_fields") or {},
                thread_id=f"{quote_id}-r{record.get('revision', 1)}",
            )
            result["human_review"] = merged.get("human_review")
            self._persist_graph_result(quote_id, tenant_id, result, include_pi=False)
        else:
            def mut(rec: dict) -> None:
                rec["status"] = merged.get("status", "review_required")
                rec["data"] = {**(rec.get("data") or {}), **merged}
                rec.setdefault("audit", []).append(
                    {"event": "submit_review", "decision": review.get("decision")}
                )

            self.store.update(quote_id, tenant_id, mut)
        updated = self.store.get(quote_id, tenant_id)
        assert updated
        return self.public_view(updated, role="reviewer", include_pi=False)

    def _persist_graph_result(
        self,
        quote_id: str,
        tenant_id: str,
        result: dict[str, Any],
        *,
        include_pi: bool,
    ) -> None:
        pi_bytes = None
        try:
            from hydroquote.contracts.models import CostBreakdown, TechnicalSelectionPackage

            inquiry = InquiryData.model_validate(result.get("inquiry") or {})
            if result.get("technical_package") and result.get("cost_breakdown"):
                tech = TechnicalSelectionPackage.model_validate(result["technical_package"])
                cost = self.engine.compute_breakdown(inquiry, tech)
                firm = (
                    result.get("status") == "ready"
                    and not cost.review_required
                    and cost.commercial_quotation is not None
                )
                # Always build preliminary doc when package exists
                try:
                    pi_bytes = build_pi_document(
                        inquiry,
                        tech,
                        cost,
                        result.get("pi_fields") or {},
                        firm=firm,
                    )
                    self._pi_cache[quote_id] = pi_bytes
                except ValueError:
                    pi_bytes = build_pi_document(
                        inquiry, tech, cost, result.get("pi_fields") or {}, firm=False
                    )
                    self._pi_cache[quote_id] = pi_bytes
        except Exception:  # noqa: BLE001
            pi_bytes = None

        def mut(rec: dict) -> None:
            rec["status"] = result.get("status", rec.get("status"))
            rec["workflow_stage"] = result.get("workflow_stage")
            rec["workflow_path"] = result.get("routing_path")
            sanitized = {k: v for k, v in result.items() if not str(k).startswith("_")}
            rec["data"] = sanitized
            if pi_bytes is not None:
                rec["data"]["pi_artifact"] = {
                    **(sanitized.get("pi_artifact") or {}),
                    "available": True,
                    "size_bytes": len(pi_bytes),
                }
            rec.setdefault("audit", []).append(
                {
                    "event": "graph_completed",
                    "status": result.get("status"),
                    "path": result.get("routing_path"),
                    "swarm_called": result.get("swarm_called"),
                }
            )

        self.store.update(quote_id, tenant_id, mut)

    def get_pi_bytes(self, quote_id: str, tenant_id: str) -> Optional[bytes]:
        if not self.store.get(quote_id, tenant_id):
            return None
        return self._pi_cache.get(quote_id)

    def public_view(
        self,
        record: dict[str, Any],
        *,
        role: str,
        include_pi: bool,
    ) -> dict[str, Any]:
        data = record.get("data") or {}
        inquiry = data.get("inquiry") or {}
        tech = data.get("technical_package") or {}
        cost = data.get("cost_breakdown") or {}
        commercial = data.get("commercial_quote") or {}

        inquiry_summary = {
            k: inquiry.get(k)
            for k in (
                "project_name",
                "net_head_m",
                "design_flow_m3s",
                "installed_capacity_kw",
                "number_of_units",
                "unit_capacity_kw",
                "turbine_type",
                "frequency_hz",
                "voltage_v",
            )
            if inquiry.get(k) is not None
        }

        # Customer-facing line items: commercial share only; never internal
        lines = []
        equipment = cost.get("equipment_costs") or {}
        commercial_total = commercial.get("total_usd") or cost.get("commercial_quotation")
        main = cost.get("main_equipment_base_cost")
        for key, line in equipment.items():
            item = {
                "equipment": line.get("display_name") or key,
                "quantity": line.get("quantity"),
            }
            if (
                role == "customer"
                and commercial_total is not None
                and main
                and float(main) > 0
                and not cost.get("review_required")
            ):
                share = float(line.get("line_total") or 0) / float(main) * float(commercial_total)
                item["customer_price_usd"] = round(share, 2)
            elif role in ("reviewer", "admin", "swarm"):
                # Swarm: technical only — still no internal cost
                if role == "swarm":
                    pass
                else:
                    item["line_total_internal_usd"] = line.get("line_total")
            lines.append(item)

        expert_state = "not_required"
        if record.get("workflow_path") == "expert_quote":
            if data.get("swarm_called") and tech:
                expert_state = "validated"
            elif data.get("swarm_called"):
                expert_state = "failed"
            else:
                expert_state = "queued"
            if record.get("status") == "review_required" and not tech:
                expert_state = "failed"

        out: dict[str, Any] = {
            "schema_version": "1.0",
            "quote_id": record["quote_id"],
            "request_id": record["request_id"],
            "status": record.get("status"),
            "workflow_path": record.get("workflow_path"),
            "workflow_stage": record.get("workflow_stage") or data.get("workflow_stage"),
            "expert_review_state": expert_state,
            "missing_fields": data.get("missing_fields") or [],
            "routing_reasons": data.get("routing_reasons") or [],
            "inquiry_summary": inquiry_summary,
            "technical_summary": {
                "recommended_turbine_type": tech.get("recommended_turbine_type"),
                "unit_count": tech.get("unit_count"),
                "unit_capacity_kw": tech.get("unit_capacity_kw"),
                "readiness": tech.get("readiness"),
                "automation_scope": tech.get("automation_scope"),
            }
            if tech
            else None,
            "equipment_customer_lines": lines if role != "swarm" else [],
            "commercial_total_usd": commercial_total
            if not cost.get("review_required")
            else None,
            "rule_version": data.get("rule_version") or cost.get("rule_version"),
            "warnings": data.get("warnings") or [],
            "pi": data.get("pi_artifact") if include_pi else {"available": bool(data.get("pi_artifact"))},
        }

        if role == "swarm":
            # Minimal technical fields for expert team
            return {
                "schema_version": "1.0",
                "quote_id": record["quote_id"],
                "status": record.get("status"),
                "inquiry_summary": inquiry_summary,
                "routing_reasons": data.get("routing_reasons") or [],
                "rule_version": out["rule_version"],
            }

        if role in ("reviewer", "admin"):
            out["review_reasons"] = cost.get("review_reasons")
            out["human_review"] = data.get("human_review")
            out["trace_events"] = [t.get("event") for t in (data.get("trace") or [])]
            # Still strip raw internal cost totals from default reviewer export unless admin
            if role == "admin":
                out["internal_cost_usd"] = cost.get("internal_cost")
                out["risk_reserve_rate"] = cost.get("risk_reserve_rate")

        if include_pi and record["quote_id"] in self._pi_cache:
            out["pi_docx_base64"] = base64.b64encode(self._pi_cache[record["quote_id"]]).decode(
                "ascii"
            )

        # Hard filter: never leak internal keys into customer payload
        if role == "customer":
            for k in list(out.keys()):
                if k in INTERNAL_COST_KEYS:
                    del out[k]
        return out
