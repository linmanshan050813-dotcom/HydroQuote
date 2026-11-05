import asyncio

import pytest

from hydroquote.llm.provider import FallbackLLM, LLMResult, parse_json_object


def test_parse_json_object_fenced():
    text = 'Here is data:\n```json\n{"net_head_m": 50, "design_flow_m3s": 6}\n```\n'
    obj = parse_json_object(text)
    assert obj["net_head_m"] == 50


@pytest.mark.asyncio
async def test_fallback_skips_missing_ibm_to_openai(monkeypatch):
    calls = []

    async def fake_openai_compatible(self, **kwargs):
        calls.append(kwargs["provider"])
        if kwargs["provider"] == "openai":
            return LLMResult(text='{"net_head_m": 50}', provider="openai", model="gpt")
        raise RuntimeError("should_not_reach_deepseek")

    async def fake_ibm(self, system, user):
        calls.append("ibm")
        raise RuntimeError("ibm_down")

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-ds")
    monkeypatch.setenv("WATSONX_API_KEY", "")
    monkeypatch.setenv("LLM_FALLBACK_ORDER", "ibm,openai,deepseek")

    llm = FallbackLLM()
    monkeypatch.setattr(FallbackLLM, "_ibm", fake_ibm)
    monkeypatch.setattr(FallbackLLM, "_openai_compatible", fake_openai_compatible)

    result = await llm.complete("sys", "user")
    assert result.provider == "openai"
    assert "ibm" in calls and "openai" in calls
