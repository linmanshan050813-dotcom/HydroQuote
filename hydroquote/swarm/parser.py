"""Parse and validate Swarm JSON into TechnicalSelectionPackage."""

from __future__ import annotations

import json
import re
from typing import Any

from hydroquote.contracts.models import TechnicalSelectionPackage
from hydroquote.domain.equipment import validate_five_equipment


def extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    # Find outermost JSON object
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        raise ValueError("no_json_object_in_swarm_output")
    return json.loads(m.group(0))


def parse_technical_package(raw: str | dict[str, Any]) -> TechnicalSelectionPackage:
    data = extract_json_object(raw) if isinstance(raw, str) else raw
    # Normalize alternate keys from schemas
    if "turbine_type" in data and "recommended_turbine_type" not in data:
        data["recommended_turbine_type"] = data.pop("turbine_type")
    if "unit_configuration" in data and isinstance(data["unit_configuration"], dict):
        uc = data.pop("unit_configuration")
        data.setdefault("unit_count", uc.get("unit_count") or uc.get("number_of_units"))
        data.setdefault("unit_capacity_kw", uc.get("unit_capacity_kw"))
    data.setdefault("selection_path", "expert_quote")
    package = TechnicalSelectionPackage.model_validate(data)
    errs = validate_five_equipment(package)
    if errs:
        raise ValueError("equipment_scope_invalid:" + ",".join(errs))
    roles = {o.role for o in package.expert_opinions}
    required = {
        "Hydraulic Expert",
        "Equipment Expert",
        "Operations Expert",
        "Risk Reviewer",
    }
    if not required.issubset(roles) and len(package.expert_opinions) < 4:
        raise ValueError("missing_expert_opinions")
    return package
