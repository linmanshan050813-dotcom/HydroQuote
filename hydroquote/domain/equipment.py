"""Equipment configuration helpers."""

from __future__ import annotations

from hydroquote.contracts.models import MAIN_EQUIPMENT_KEYS, TechnicalSelectionPackage


def validate_five_equipment(package: TechnicalSelectionPackage) -> list[str]:
    codes = [e.code for e in package.equipment_scope]
    errors: list[str] = []
    for key in MAIN_EQUIPMENT_KEYS:
        if key not in codes:
            errors.append(f"missing_equipment:{key}")
    extras = set(codes) - set(MAIN_EQUIPMENT_KEYS)
    for e in extras:
        errors.append(f"unexpected_equipment:{e}")
    if len(codes) != len(set(codes)):
        errors.append("duplicate_equipment_entries")
    return errors
