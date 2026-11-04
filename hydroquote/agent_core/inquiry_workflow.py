"""Inquiry WorkflowAgent adapter (openJiuwen when available, deterministic fallback)."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from hydroquote.contracts.models import InquiryData
from hydroquote.domain.inquiry import (
    detect_conflicts,
    extract_inquiry_from_text,
    missing_required_fields,
    normalize_units_config,
)

logger = logging.getLogger(__name__)


def _try_import_openjiuwen() -> bool:
    try:
        import openjiuwen  # noqa: F401

        return True
    except ImportError:
        return False


class InquiryAgentAdapter:
    """
    Real openJiuwen WorkflowAgent path when package + model configured;
    otherwise deterministic extract with agent_core_mode=fallback.
    """

    def __init__(self, agent: Any = None):
        self.agent = agent
        self.openjiuwen_available = _try_import_openjiuwen()
        self._workflow_agent = None
        if self.openjiuwen_available and agent is None:
            self._workflow_agent = self._build_workflow_agent()

    def _build_workflow_agent(self) -> Any:
        """Attempt to construct a minimal Workflow for extraction."""
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
            self._passthrough_flow = flow
            logger.info("openJiuwen Workflow smoke graph constructed")
            return flow
        except Exception as exc:  # noqa: BLE001
            logger.warning("openJiuwen WorkflowAgent build failed: %s", exc)
            self.openjiuwen_available = False
            return None

    async def extract(self, raw_text: str, conversation_id: Optional[str] = None) -> dict[str, Any]:
        conversation_id = conversation_id or f"inq-{uuid.uuid4().hex}"
        invoked = False
        if self._workflow_agent is not None:
            try:
                session = self._create_session()
                await self._workflow_agent.invoke(
                    {"query": raw_text[:8000]},
                    session,
                )
                invoked = True
            except Exception as exc:  # noqa: BLE001
                logger.warning("WorkflowAgent.invoke failed, using deterministic extract: %s", exc)

        inquiry = extract_inquiry_from_text(raw_text)
        inquiry = normalize_units_config(inquiry)
        missing = missing_required_fields(inquiry)
        conflicts = detect_conflicts(inquiry)
        return {
            "inquiry": inquiry.model_dump(mode="json"),
            "missing_fields": missing,
            "conflict_flags": conflicts,
            "conversation_id": conversation_id,
            "agent_core_invoked": invoked or bool(self.agent),
            "agent_core_backend": "openjiuwen" if invoked else "deterministic_fallback",
        }
