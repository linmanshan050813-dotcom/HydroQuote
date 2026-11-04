from hydroquote.swarm.parser import parse_technical_package


SAMPLE = {
    "recommended_turbine_type": "Francis",
    "unit_count": 2,
    "unit_capacity_kw": 1200,
    "hydraulic_calculation": {"ok": True},
    "equipment_scope": [
        {"code": "hydro_turbine", "name": "Hydro Turbine", "quantity": 2},
        {"code": "generator_avr", "name": "Generator and Exciter / AVR", "quantity": 2},
        {"code": "speed_governor", "name": "Speed Governor", "quantity": 2},
        {"code": "inlet_valve", "name": "Inlet Valve", "quantity": 2},
        {"code": "automation_system", "name": "Automation System", "quantity": 2},
    ],
    "expert_opinions": [
        {"role": "Hydraulic Expert", "analysis": "ok"},
        {"role": "Equipment Expert", "analysis": "ok"},
        {"role": "Operations Expert", "analysis": "ok"},
        {"role": "Risk Reviewer", "analysis": "ok"},
    ],
    "discussion_summary": "aligned",
    "cross_review": "passed",
    "readiness": "preliminary_ready",
    "selection_path": "expert_quote",
}


def test_parse_ok():
    pkg = parse_technical_package(SAMPLE)
    assert pkg.recommended_turbine_type == "Francis"
    assert len(pkg.expert_opinions) == 4
