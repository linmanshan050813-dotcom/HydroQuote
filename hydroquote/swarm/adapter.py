"""JiuwenSwarm CLI adapter — serial queue, no shell injection."""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import uuid
from typing import Any, Optional

from hydroquote.swarm.parser import parse_technical_package
from hydroquote.swarm.prompt import build_team_prompt

logger = logging.getLogger(__name__)

_queue_lock = asyncio.Lock()


class SwarmAdapter:
    def __init__(
        self,
        *,
        cli_path: Optional[str] = None,
        timeout_s: int = 300,
        enabled: Optional[bool] = None,
    ):
        self.cli_path = cli_path or shutil.which("jiuwenswarm") or "jiuwenswarm"
        self.timeout_s = timeout_s
        env_flag = os.getenv("HYDROQUOTE_SWARM_ENABLED", "").lower()
        if enabled is not None:
            self.enabled = enabled
        else:
            self.enabled = env_flag in ("1", "true", "yes")

    def is_available(self) -> bool:
        if not self.enabled:
            return False
        return shutil.which(self.cli_path) is not None or os.path.isfile(self.cli_path)

    async def run_expert_selection(
        self,
        *,
        quote_id: str,
        routing_reasons: list[str],
        rule_version: str,
        session_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Returns dict with keys: ok, package|None, error, expert_run_id, raw_excerpt, backend
        """
        expert_run_id = f"SWARM-{uuid.uuid4().hex[:10]}"
        session_id = session_id or f"hydroquote-{quote_id}"
        prompt = build_team_prompt(quote_id, routing_reasons, rule_version)

        if not self.is_available():
            return {
                "ok": False,
                "package": None,
                "error": "jiuwenswarm_unavailable",
                "expert_run_id": expert_run_id,
                "raw_excerpt": None,
                "backend": "unavailable",
                "review_required": True,
            }

        async with _queue_lock:
            try:
                proc = await asyncio.create_subprocess_exec(
                    self.cli_path,
                    "chat",
                    "--mode",
                    "team",
                    "--session",
                    session_id,
                    "--json",
                    "--timeout",
                    str(self.timeout_s),
                    prompt,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                try:
                    stdout, stderr = await asyncio.wait_for(
                        proc.communicate(), timeout=self.timeout_s + 30
                    )
                except asyncio.TimeoutError:
                    proc.kill()
                    return {
                        "ok": False,
                        "package": None,
                        "error": "swarm_timeout",
                        "expert_run_id": expert_run_id,
                        "raw_excerpt": None,
                        "backend": "cli",
                        "review_required": True,
                    }
                text = (stdout or b"").decode("utf-8", errors="replace")
                err = (stderr or b"").decode("utf-8", errors="replace")
                if proc.returncode != 0:
                    logger.warning("jiuwenswarm exit %s: %s", proc.returncode, err[:500])
                    return {
                        "ok": False,
                        "package": None,
                        "error": f"swarm_exit_{proc.returncode}",
                        "expert_run_id": expert_run_id,
                        "raw_excerpt": (text or err)[:2000],
                        "backend": "cli",
                        "review_required": True,
                    }
                package = parse_technical_package(text)
                return {
                    "ok": True,
                    "package": package.model_dump(mode="json"),
                    "error": None,
                    "expert_run_id": expert_run_id,
                    "raw_excerpt": text[:2000],
                    "backend": "cli",
                    "review_required": package.readiness == "needs_human_review"
                    or package.technical_approval_required,
                }
            except FileNotFoundError:
                return {
                    "ok": False,
                    "package": None,
                    "error": "jiuwenswarm_not_found",
                    "expert_run_id": expert_run_id,
                    "raw_excerpt": None,
                    "backend": "unavailable",
                    "review_required": True,
                }
            except Exception as exc:  # noqa: BLE001
                logger.exception("SwarmAdapter failure")
                return {
                    "ok": False,
                    "package": None,
                    "error": f"swarm_error:{type(exc).__name__}",
                    "expert_run_id": expert_run_id,
                    "raw_excerpt": None,
                    "backend": "cli",
                    "review_required": True,
                }
