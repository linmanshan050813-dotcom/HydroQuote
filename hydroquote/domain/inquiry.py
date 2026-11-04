"""Inquiry normalization, required-field checks, conflict detection."""

from __future__ import annotations

import re
from typing import Any

from hydroquote.contracts.models import InquiryData

REQUIRED_FOR_SELECTION = (
    "net_head_m",
    "design_flow_m3s",
    "installed_capacity_kw",
)


def extract_inquiry_from_text(text: str) -> InquiryData:
    """Deterministic regex extraction (Agent Core may enrich; this is baseline)."""
    lower = text.lower()
    data: dict[str, Any] = {"source_provenance": ["regex_extract"], "field_evidence": {}}

    def _first_float(patterns: list[str]) -> float | None:
        for pat in patterns:
            m = re.search(pat, lower, re.I)
            if m:
                return float(m.group(1))
        return None

    head = _first_float(
        [
            r"net\s*head[:\s]+(\d+(?:\.\d+)?)\s*m",
            r"head[:\s]+(\d+(?:\.\d+)?)\s*m",
            r"(\d+(?:\.\d+)?)\s*m\s*(?:net\s*)?head",
        ]
    )
    if head is not None:
        data["net_head_m"] = head
        data["field_evidence"]["net_head_m"] = "regex"

    flow = _first_float(
        [
            r"design\s*flow[:\s]+(\d+(?:\.\d+)?)\s*m",
            r"flow[:\s]+(\d+(?:\.\d+)?)\s*m[³3]?/?s",
            r"(\d+(?:\.\d+)?)\s*m[³3]/s",
        ]
    )
    if flow is not None:
        data["design_flow_m3s"] = flow
        data["field_evidence"]["design_flow_m3s"] = "regex"

    cap = _first_float(
        [
            r"installed\s*capacity[:\s]+(\d+(?:\.\d+)?)\s*kw",
            r"(\d+(?:\.\d+)?)\s*kw",
            r"(\d+(?:\.\d+)?)\s*mw",
        ]
    )
    if cap is not None:
        if re.search(r"(\d+(?:\.\d+)?)\s*mw", lower) and not re.search(r"\d+\s*kw", lower):
            cap = cap * 1000.0
        data["installed_capacity_kw"] = cap
        data["field_evidence"]["installed_capacity_kw"] = "regex"

    units = re.search(r"(\d+)\s*[×x]\s*(\d+(?:\.\d+)?)\s*kw", lower)
    if units:
        data["number_of_units"] = int(units.group(1))
        data["unit_capacity_kw"] = float(units.group(2))
        data["field_evidence"]["unit_configuration"] = "regex"
    elif data.get("installed_capacity_kw"):
        nu = re.search(r"(\d+)\s*units?", lower)
        if nu:
            data["number_of_units"] = int(nu.group(1))
            data["unit_capacity_kw"] = data["installed_capacity_kw"] / data["number_of_units"]

    freq = _first_float([r"(\d+)\s*hz"])
    if freq is not None:
        data["frequency_hz"] = freq

    volt = _first_float([r"(\d+(?:\.\d+)?)\s*k?v(?:olt)?"])
    if volt is not None:
        if volt < 100:  # likely kV
            volt *= 1000.0
        data["voltage_v"] = volt

    for t in ("Francis", "Kaplan", "Pelton", "Tubular", "Bulb", "Cross-flow"):
        if t.lower() in lower or t.lower().replace("-", " ") in lower:
            data["turbine_type"] = t
            break

    if "sediment" in lower and any(w in lower for w in ("high", "abras", "sand")):
        data["sediment_load"] = "high"
    if "seasonal" in lower or "dry season" in lower:
        data["flow_variability"] = "seasonal"
    if "expert" in lower and "review" in lower:
        data["customer_requests_expert_review"] = True

    name = re.search(r"project\s*name[:\s]+(.+)", text, re.I)
    if name:
        data["project_name"] = name.group(1).strip().splitlines()[0][:250]

    return InquiryData.model_validate(data)


def missing_required_fields(inquiry: InquiryData) -> list[str]:
    missing: list[str] = []
    for f in REQUIRED_FOR_SELECTION:
        if getattr(inquiry, f) is None:
            missing.append(f)
    if inquiry.number_of_units is None and inquiry.unit_capacity_kw is None:
        # can derive from installed if units known later; still allow if installed set
        if inquiry.installed_capacity_kw is None:
            missing.append("unit_configuration")
    return missing


def detect_conflicts(inquiry: InquiryData) -> list[str]:
    flags: list[str] = []
    if (
        inquiry.number_of_units
        and inquiry.unit_capacity_kw
        and inquiry.installed_capacity_kw
    ):
        expected = inquiry.number_of_units * inquiry.unit_capacity_kw
        if abs(expected - inquiry.installed_capacity_kw) > max(1.0, 0.02 * inquiry.installed_capacity_kw):
            flags.append("unit_capacity_vs_installed_mismatch")
    if inquiry.net_head_m is not None and inquiry.net_head_m <= 0:
        flags.append("invalid_net_head")
    if inquiry.design_flow_m3s is not None and inquiry.design_flow_m3s <= 0:
        flags.append("invalid_design_flow")
    return flags


def normalize_units_config(inquiry: InquiryData) -> InquiryData:
    """Fill unit_count / unit_capacity when possible."""
    data = inquiry.model_dump()
    if data.get("installed_capacity_kw") and data.get("number_of_units") and not data.get("unit_capacity_kw"):
        data["unit_capacity_kw"] = data["installed_capacity_kw"] / data["number_of_units"]
    elif data.get("installed_capacity_kw") and data.get("unit_capacity_kw") and not data.get("number_of_units"):
        data["number_of_units"] = max(1, int(round(data["installed_capacity_kw"] / data["unit_capacity_kw"])))
    elif data.get("installed_capacity_kw") and not data.get("number_of_units"):
        data["number_of_units"] = 1
        data["unit_capacity_kw"] = data["installed_capacity_kw"]
    return InquiryData.model_validate(data)
