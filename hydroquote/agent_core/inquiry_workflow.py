"""Inquiry adapter: LLM extract (IBM→OpenAI→DeepSeek) then deterministic merge."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Optional

from hydroquote.contracts.models import InquiryData
from hydroquote.domain.inquiry import (
    detect_conflicts,
    extract_inquiry_from_text,
    missing_required_fields,
    normalize_units_config,
)
from hydroquote.llm.provider import (
    INQUIRY_EXTRACT_SYSTEM,
    get_fallback_llm,
    parse_json_object,
)

logger = logging.getLogger(__name__)


def _try_import_openjiuwen() -> bool:
    try:
        import openjiuwen  # noqa: F401

        return True
    except ImportError:
        return False


def _merge_inquiry(base: InquiryData, overlay: dict[str, Any]) -> InquiryData:
    data = base.model_dump()
    for key, value in overlay.items():
        if key not in data:
            continue
        if value is None or value == "":
            continue
        if data.get(key) is None:
            data[key] = value
    provenance = list(data.get("source_provenance") or [])
    if "llm_extract" not in provenance:
        provenance.append("llm_extract")
    data["source_provenance"] = provenance
    evidence = dict(data.get("field_evidence") or {})
    for key, value in overlay.items():
        if key in InquiryData.model_fields and value is not None and value != "":
            evidence.setdefault(key, "llm")
    data["field_evidence"] = evidence
    return InquiryData.model_validate(data)


class InquiryAgentAdapter:
    """
    Prefer FallbackLLM (ibm → openai → deepseek) for structured extraction.
    Always merge with regex extract; never invent money.
    """

    def __init__(self, agent: Any = None, llm: Any = None):
        self.agent = agent
        self.llm = llm or get_fallback_llm()
        self.openjiuwen_available = _try_import_openjiuwen()
        self._workflow_agent = None
        if self.openjiuwen_available and agent is None:
            self._workflow_agent = self._build_workflow_agent()

    def _build_workflow_agent(self) -> Any:
        try:
            from openjiuwen.core.workflow import (  # type: ignore
                End,
                Start,
                Workflow,
                create_workflow_session,
            )

            self._create_session = create_workflow_session
            flow = Workflow()
            flow.set_start_comp("start", Start(), inputs_schema={"query": "${query}"})
            flow.set_end_comp(
                "end",
                End({"response_template": "{{result}}"}),
                inputs_schema={"result": "${start.query}"},
            )
            flow.add_connection("start", "end")
            logger.info("openJiuwen Workflow smoke graph constructed")
            return flow
        except Exception as exc:  # noqa: BLE001
            logger.warning("openJiuwen WorkflowAgent build failed: %s", exc)
            self.openjiuwen_available = False
            return None

    async def extract(self, raw_text: str, conversation_id: Optional[str] = None) -> dict[str, Any]:
        conversation_id = conversation_id or f"inq-{uuid.uuid4().hex}"
        backend = "deterministic_fallback"
        invoked = False
        llm_provider = None

        # Optional openJiuwen smoke invoke (non-authoritative)
        if self._workflow_agent is not None:
            try:
                session = self._create_session()
                await self._workflow_agent.invoke({"query": raw_text[:8000]}, session)
                invoked = True
            except Exception as exc:  # noqa: BLE001
                logger.warning("WorkflowAgent.invoke failed: %s", exc)

        inquiry = extract_inquiry_from_text(raw_text)

        # Authoritative LLM path with provider fallback
        llm_started = time.perf_counter()
        llm_attempts: list[dict[str, Any]] = []
        try:
            result = await self.llm.complete(
                INQUIRY_EXTRACT_SYSTEM,
                f"Extract parameters from this inquiry text:\n\n{raw_text[:12000]}",
            )
            overlay = parse_json_object(result.text)
            inquiry = _merge_inquiry(inquiry, overlay)
            backend = f"llm:{result.provider}"
            llm_provider = result.provider
            llm_attempts = list(result.attempts or [])
            invoked = True
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM extract unavailable, regex-only: %s", exc)
            backend = "deterministic_fallback"
            llm_attempts = list(getattr(exc, "llm_attempts", None) or [])
        llm_elapsed_ms = round((time.perf_counter() - llm_started) * 1000, 1)

        inquiry = normalize_units_config(inquiry)
        missing = missing_required_fields(inquiry)
        conflicts = detect_conflicts(inquiry)
        return {
            "inquiry": inquiry.model_dump(mode="json"),
            "missing_fields": missing,
            "conflict_flags": conflicts,
            "conversation_id": conversation_id,
            "agent_core_invoked": invoked or bool(self.agent),
            "agent_core_backend": backend,
            "llm_provider": llm_provider,
            "llm_elapsed_ms": llm_elapsed_ms,
            "llm_attempts": llm_attempts,
        }
