"""PI generation — never invent bank/HS/delivery terms."""

from __future__ import annotations

import io
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from docx import Document

from hydroquote.contracts.models import CostBreakdown, InquiryData, TechnicalSelectionPackage


REQUIRED_PI_FIELDS = (
    "supplier_name",
    "bank_account",
    "payment_terms",
    "delivery_terms",
    "hs_code",
    "delivery_date",
)


def pi_readiness(pi_fields: dict[str, Any] | None) -> tuple[bool, list[str]]:
    fields = pi_fields or {}
    missing = [k for k in REQUIRED_PI_FIELDS if not fields.get(k)]
    return (len(missing) == 0, missing)


def build_pi_document(
    inquiry: InquiryData,
    technical: TechnicalSelectionPackage,
    cost: CostBreakdown,
    pi_fields: dict[str, Any] | None,
    *,
    firm: bool,
) -> bytes:
    """Return DOCX bytes. Firm PI only when firm=True and commercial total present."""
    ok, missing = pi_readiness(pi_fields)
    if firm and (not ok or cost.commercial_quotation is None or cost.review_required):
        raise ValueError(f"cannot_issue_firm_pi:missing={missing}")

    doc = Document()
    title = "PROFORMA INVOICE" if firm else "PROFORMA INVOICE (PRELIMINARY — NOT BINDING)"
    doc.add_heading(title, 0)
    doc.add_paragraph(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    doc.add_paragraph(f"Project: {inquiry.project_name or 'N/A'}")
    doc.add_paragraph(
        f"Turbine: {technical.recommended_turbine_type} × {technical.unit_count} "
        f"@ {technical.unit_capacity_kw} kW"
    )
    doc.add_paragraph(f"Rule version: {cost.rule_version}")

    doc.add_heading("Equipment Lines (customer view)", level=1)
    # Customer-facing: show commercial-scaled share only when firm; else mark TBD
    for key, line in cost.equipment_costs.items():
        if cost.commercial_quotation and cost.main_equipment_base_cost > 0 and not cost.review_required:
            share = (line.line_total / cost.main_equipment_base_cost) * cost.commercial_quotation
            amount = f"USD {share.quantize(Decimal('0.01'))}"
        else:
            amount = "TBD (review_required)" if cost.review_required else f"USD {line.line_total}"
        doc.add_paragraph(f"{line.display_name}: {amount} (qty {line.quantity})")

    if cost.commercial_quotation is not None and not cost.review_required:
        doc.add_paragraph(f"Total Commercial Quotation: USD {cost.commercial_quotation}")
    else:
        doc.add_paragraph("Total Commercial Quotation: PENDING REVIEW")

    fields = pi_fields or {}
    doc.add_heading("Commercial Terms", level=1)
    for k in REQUIRED_PI_FIELDS:
        val = fields.get(k)
        if not val:
            doc.add_paragraph(f"{k}: [NOT PROVIDED — not invented]")
        else:
            doc.add_paragraph(f"{k}: {val}")

    if not firm:
        doc.add_paragraph(
            "This document is preliminary and does not constitute a firm commercial commitment."
        )

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
