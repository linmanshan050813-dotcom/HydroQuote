from hydroquote.contracts.models import InquiryData
from hydroquote.orchestration.router import route_after_inquiry


def _base(**kwargs):
    data = dict(
        net_head_m=50,
        design_flow_m3s=6,
        installed_capacity_kw=2400,
        number_of_units=2,
        unit_capacity_kw=1200,
    )
    data.update(kwargs)
    return InquiryData(**data)


def test_missing_head_needs_input():
    path, reasons = route_after_inquiry(_base(net_head_m=None), confirmed=True)
    assert path == "needs_input"
    assert any("net_head" in r for r in reasons)


def test_standard_fast():
    path, reasons = route_after_inquiry(_base(), confirmed=True)
    assert path == "fast_quote"


def test_sediment_expert():
    path, reasons = route_after_inquiry(_base(sediment_load="high"), confirmed=True)
    assert path == "expert_quote"
    assert reasons
