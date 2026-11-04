"""Rule-based Fast / Expert complexity router."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml

from hydroquote.contracts.models import InquiryData
from hydroquote.domain.inquiry import missing_required_fields

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RULES = ROOT / "config" / "complexity_rules.yaml"


def load_complexity_rules(path: Path | None = None) -> dict[str, Any]:
    with open(path or DEFAULT_RULES, encoding="utf-8") as f:
        return yaml.safe_load(f)


def route_after_inquiry(
    inquiry: InquiryData,
    *,
    confirmed: bool = True,
    rules: dict[str, Any] | None = None,
) -> tuple[Literal["needs_input", "fast_quote", "expert_quote"], list[str]]:
    missing = missing_required_fields(inquiry)
    if missing or not confirmed:
        return "needs_input", [f"missing:{m}" for m in missing] or ["not_confirmed"]

    rules = rules or load_complexity_rules()
    reasons: list[str] = []
    for signal in rules.get("expert_signals", []):
        field = signal["field"]
        value = getattr(inquiry, field, None)
        when = signal.get("when")
        hit = False
        if when == "eq":
            hit = value == signal.get("value")
        elif when == "in":
            hit = value in (signal.get("values") or [])
        if hit:
            reasons.append(signal.get("reason") or signal.get("id"))

    if reasons:
        return "expert_quote", reasons
    return "fast_quote", ["standard_project_covered_by_rules"]
