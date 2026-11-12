"""Multi-provider LLM with fallback: IBM watsonx → OpenAI → DeepSeek."""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


@dataclass
class LLMResult:
    text: str
    provider: str
    model: str
    elapsed_ms: float = 0
    attempts: list[dict[str, Any]] = field(default_factory=list)


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def _is_usable_key(value: str) -> bool:
    if not value:
        return False
    lowered = value.lower()
    return not (
        lowered.startswith("your_")
        or lowered in {"changeme", "placeholder", "xxx", "none", "null"}
    )


class FallbackLLM:
    """
    Try providers in order. Default: ibm → openai → deepseek.
    Pricing / Domain layer must never call this for money arithmetic.
    """

    def __init__(self, order: Optional[list[str]] = None):
        raw = _env("LLM_FALLBACK_ORDER", "ibm,openai,deepseek")
        self.order = order or [p.strip().lower() for p in raw.split(",") if p.strip()]
        self.temperature = float(_env("LLM_TEMPERATURE", "0") or "0")
        self.max_tokens = int(_env("LLM_MAX_TOKENS", "2000") or "2000")

    async def complete(self, system: str, user: str) -> LLMResult:
        errors: list[str] = []
        attempts: list[dict[str, Any]] = []
        started = time.perf_counter()
        for name in self.order:
            attempt_started = time.perf_counter()
            try:
                if name == "ibm":
                    result = await self._ibm(system, user)
                elif name in ("openai", "chatgpt"):
                    result = await self._openai_compatible(
                        provider="openai",
                        api_key=_env("OPENAI_API_KEY"),
                        base_url=_env("OPENAI_API_BASE", "https://api.openai.com/v1"),
                        model=_env("OPENAI_MODEL", "gpt-4o-mini"),
                        system=system,
                        user=user,
                    )
                elif name == "deepseek":
                    result = await self._openai_compatible(
                        provider="deepseek",
                        api_key=_env("DEEPSEEK_API_KEY"),
                        base_url=_env("DEEPSEEK_API_BASE", "https://api.deepseek.com"),
                        model=_env("DEEPSEEK_MODEL", "deepseek-chat"),
                        system=system,
                        user=user,
                    )
                else:
                    errors.append(f"{name}:unknown_provider")
                    attempts.append(
                        {
                            "provider": name,
                            "elapsed_ms": round((time.perf_counter() - attempt_started) * 1000, 1),
                            "ok": False,
                            "error": "unknown_provider",
                        }
                    )
                    continue
                attempts.append(
                    {
                        "provider": result.provider,
                        "elapsed_ms": round((time.perf_counter() - attempt_started) * 1000, 1),
                        "ok": True,
                    }
                )
                result.elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
                result.attempts = attempts
                return result
            except Exception as exc:  # noqa: BLE001
                msg = f"{name}:{type(exc).__name__}:{exc}"
                logger.warning("LLM provider failed: %s", msg)
                errors.append(msg)
                attempts.append(
                    {
                        "provider": name,
                        "elapsed_ms": round((time.perf_counter() - attempt_started) * 1000, 1),
                        "ok": False,
                        "error": type(exc).__name__,
                    }
                )
        failure = RuntimeError("all_llm_providers_failed:" + " | ".join(errors))
        failure.llm_attempts = attempts  # type: ignore[attr-defined]
        raise failure

    async def _openai_compatible(
        self,
        *,
        provider: str,
        api_key: str,
        base_url: str,
        model: str,
        system: str,
        user: str,
    ) -> LLMResult:
        if not _is_usable_key(api_key):
            raise RuntimeError(f"{provider}_api_key_missing")
        url = base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code >= 400:
                raise RuntimeError(f"{provider}_http_{resp.status_code}:{resp.text[:300]}")
            data = resp.json()
        text = data["choices"][0]["message"]["content"]
        return LLMResult(text=text, provider=provider, model=model)

    async def _ibm(self, system: str, user: str) -> LLMResult:
        api_key = _env("WATSONX_API_KEY")
        project_id = _env("WATSONX_PROJECT_ID")
        base = _env("WATSONX_URL", "https://us-south.ml.cloud.ibm.com").rstrip("/")
        model = _env("WATSONX_MODEL", "ibm/granite-13b-chat-v2")
        if not _is_usable_key(api_key) or not project_id:
            raise RuntimeError("ibm_watsonx_credentials_missing")

        # IAM token
        async with httpx.AsyncClient(timeout=60.0) as client:
            token_resp = await client.post(
                "https://iam.cloud.ibm.com/identity/token",
                data={
                    "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                    "apikey": api_key,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if token_resp.status_code >= 400:
                raise RuntimeError(f"ibm_iam_{token_resp.status_code}:{token_resp.text[:200]}")
            access_token = token_resp.json()["access_token"]

            gen_url = f"{base}/ml/v1/text/generation?version=2023-05-29"
            prompt = f"System:\n{system}\n\nUser:\n{user}\n\nAssistant:"
            body = {
                "model_id": model,
                "input": prompt,
                "project_id": project_id,
                "parameters": {
                    "decoding_method": "greedy",
                    "max_new_tokens": min(self.max_tokens, 2000),
                    "temperature": self.temperature,
                },
            }
            gen_resp = await client.post(
                gen_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json=body,
            )
            if gen_resp.status_code >= 400:
                raise RuntimeError(f"ibm_gen_{gen_resp.status_code}:{gen_resp.text[:300]}")
            results = gen_resp.json().get("results") or []
            if not results:
                raise RuntimeError("ibm_empty_generation")
            text = results[0].get("generated_text") or ""
            if not text.strip():
                raise RuntimeError("ibm_empty_text")
        return LLMResult(text=text, provider="ibm", model=model)


_singleton: Optional[FallbackLLM] = None


def get_fallback_llm() -> FallbackLLM:
    global _singleton
    if _singleton is None:
        _singleton = FallbackLLM()
    return _singleton


INQUIRY_EXTRACT_SYSTEM = """You extract hydro-turbine project inquiry parameters.
Return ONLY a JSON object (no markdown) with any of these keys when present:
project_name, project_country, project_location, customer_company,
net_head_m, design_flow_m3s, installed_capacity_kw, number_of_units,
unit_capacity_kw, voltage_v, frequency_hz, turbine_type,
automation_level (Basic|Standard|Advanced),
sediment_load, flow_variability,
special_control_required (bool), customer_requests_expert_review (bool),
turbine_type_ambiguous (bool), boundary_head_condition (bool),
hydraulic_power_conflict (bool), efficiency.
Use SI numbers. Net head must be net head in meters. Do not invent missing values; omit unknown keys.
"""


def parse_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        raise ValueError("no_json_in_llm_output")
    return json.loads(m.group(0))
