"""Engineering / Fast selection WorkflowAgent adapter."""

from __future__ import annotations

import logging
from typing import Any

from hydroquote.contracts.models import InquiryData
from hydroquote.domain.selection import build_fast_technical_package

logger = logging.getLogger(__name__)


class EngineeringAgentAdapter:
    """Fast path: pure Python rules; optional Agent Core explanation hook."""

    def __init__(self, agent: Any = None):
        self.agent = agent

    async def fast_select(self, inquiry_dict: dict[str, Any]) -> dict[str, Any]:
        inquiry = InquiryData.model_validate(inquiry_dict)
        package = build_fast_technical_package(inquiry)
        explanation = None
        agent_invoked = False
        if self.agent is not None:
            try:
                explanation = await self.agent.invoke({"inquiry": inquiry_dict})
                agent_invoked = True
            except Exception as exc:  # noqa: BLE001
                logger.warning("Engineering agent invoke failed: %s", exc)
        data = package.model_dump(mode="json")
        return {
            "technical_package": data,
            "selection_explanation": explanation,
            "agent_core_invoked": agent_invoked,
        }
