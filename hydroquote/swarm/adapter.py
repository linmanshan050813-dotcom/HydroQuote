"""JiuwenSwarm CLI adapter — serial queue, no shell injection."""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import time
import uuid
from typing import Any, Optional

from hydroquote.orchestration.latency import stage_record
from hydroquote.swarm.parser import parse_technical_package
from hydroquote.swarm.prompt import build_leader_decision_prompt, build_team_prompt

logger = logging.getLogger(__name__)

_queue_lock = asyncio.Lock()


class _ChatPipes:
    """One stdout/stderr reader for the life of a chat process."""

    def __init__(self, proc: asyncio.subprocess.Process):
        self.proc = proc
        self.stdout = bytearray()
        self.stderr = bytearray()
        self._out = asyncio.create_task(SwarmAdapter._pump(proc.stdout, self.stdout))
        self._err = asyncio.create_task(SwarmAdapter._pump(proc.stderr, self.stderr))

    async def wait(self, timeout_s: float) -> Optional[int]:
        """Return the exit code, or None if the budget ended and the process is still alive."""
        try:
            await asyncio.wait_for(self.proc.wait(), timeout=timeout_s)
        except asyncio.TimeoutError:
            return None
        await self._out
        await self._err
        return self.proc.returncode

    def text(self) -> tuple[str, str]:
        return (
            self.stdout.decode("utf-8", errors="replace"),
            self.stderr.decode("utf-8", errors="replace"),
        )

    async def aclose(self) -> None:
        await SwarmAdapter._release(self.proc)
        try:
            await asyncio.wait_for(asyncio.gather(self._out, self._err), timeout=2)
        except asyncio.TimeoutError:
            self._out.cancel()
            self._err.cancel()
            await asyncio.gather(self._out, self._err, return_exceptions=True)


class SwarmAdapter:
    def __init__(
        self,
        *,
        cli_path: Optional[str] = None,
        timeout_s: int = 300,
        leader_grace_s: int = 60,
        enabled: Optional[bool] = None,
        command: Optional[list[str]] = None,
    ):
        self.cli_path = cli_path or shutil.which("jiuwenswarm") or "jiuwenswarm"
        self.timeout_s = timeout_s
        # Slice of timeout_s reserved for the leader decision. The discussion
        # clock must not consume the whole budget, or the leader never speaks.
        self.leader_grace_s = max(1, min(leader_grace_s, max(1, timeout_s - 1)))
        self._command = command or [self.cli_path]
        env_flag = os.getenv("HYDROQUOTE_SWARM_ENABLED", "").lower()
        if enabled is not None:
            self.enabled = enabled
        else:
            self.enabled = env_flag in ("1", "true", "yes")

    def is_available(self) -> bool:
        if not self.enabled:
            return False
        exe = self._command[0]
        if shutil.which(exe) is None and not os.path.isfile(exe):
            return False
        script = next((part for part in self._command[1:] if part.endswith(".py")), None)
        if script is not None and not os.path.isfile(script):
            return False
        return True

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
        discuss_s = max(1, self.timeout_s - self.leader_grace_s)
        prompt = build_team_prompt(
            quote_id,
            routing_reasons,
            rule_version,
            discuss_timeout_s=discuss_s,
        )
        leader_prompt = build_leader_decision_prompt(quote_id, routing_reasons, rule_version)
        stages: list[dict[str, Any]] = []

        available_started = time.perf_counter()
        available = self.is_available()
        stages.append(stage_record("availability_check", available_started, available=available))
        if not available:
            return self._failure(
                error="jiuwenswarm_unavailable",
                expert_run_id=expert_run_id,
                backend="unavailable",
                stages=stages,
            )

        # Time spent blocked here is another team chat holding the single CLI channel.
        queue_started = time.perf_counter()
        async with _queue_lock:
            stages.append(stage_record("queue_wait", queue_started))
            try:
                return await self._run_team_then_leader(
                    session_id=session_id,
                    prompt=prompt,
                    leader_prompt=leader_prompt,
                    discuss_s=discuss_s,
                    expert_run_id=expert_run_id,
                    stages=stages,
                )
            except FileNotFoundError:
                stages.append(
                    stage_record(
                        "process_spawn",
                        time.perf_counter(),
                        ok=False,
                        error="jiuwenswarm_not_found",
                    )
                )
                return self._failure(
                    error="jiuwenswarm_not_found",
                    expert_run_id=expert_run_id,
                    backend="unavailable",
                    stages=stages,
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("SwarmAdapter failure")
                return self._failure(
                    error=f"swarm_error:{type(exc).__name__}",
                    expert_run_id=expert_run_id,
                    backend="cli",
                    stages=stages,
                )

    async def _run_team_then_leader(
        self,
        *,
        session_id: str,
        prompt: str,
        leader_prompt: str,
        discuss_s: int,
        expert_run_id: str,
        stages: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Discussion stays alive at the time limit and the leader closes it.

        The discussion budget is not a kill switch. When it ends, the same
        session is told to stop and emit one TechnicalSelectionPackage. A second
        full expert meeting is not started.
        """
        spawn_started = time.perf_counter()
        proc = await self._spawn(session_id, prompt, timeout_s=self.timeout_s)
        pipes = _ChatPipes(proc)
        stages.append(stage_record("process_spawn", spawn_started, ok=True))
        discuss_started = time.perf_counter()
        discuss_code = await pipes.wait(discuss_s)
        discuss_text, discuss_err = pipes.text()
        if discuss_code is None:
            # Budget is over and the meeting process is still running. Hand the
            # same process to the leader instead of killing it.
            await self._send_leader_close(proc, leader_prompt)
            leader_started = time.perf_counter()
            code = await pipes.wait(self.leader_grace_s)
            text, err = pipes.text()
            stages.append(
                stage_record(
                    "leader_decision",
                    leader_started,
                    ok=code == 0,
                    leader_closed=True,
                    same_process=True,
                )
            )
            stages.append(
                stage_record(
                    "cli_wall",
                    discuss_started,
                    ok=code == 0,
                    timeout_s=self.timeout_s,
                    returncode=code,
                )
            )
            package = self._try_package(text)
            if package is not None:
                return self._success(package, text, expert_run_id, stages)
            await pipes.aclose()
            return await self._leader_followup(
                session_id=session_id,
                leader_prompt=leader_prompt,
                expert_run_id=expert_run_id,
                stages=stages,
                prior_excerpt=text or err,
            )

        stages.append(
            stage_record(
                "cli_wall",
                discuss_started,
                ok=discuss_code == 0,
                timeout_s=self.timeout_s,
                returncode=discuss_code,
            )
        )
        package = self._try_package(discuss_text)
        if package is not None:
            return self._success(package, discuss_text, expert_run_id, stages)
        if discuss_code not in (0, None):
            logger.warning("jiuwenswarm exit %s: %s", discuss_code, (discuss_err or "")[:500])
        return await self._leader_followup(
            session_id=session_id,
            leader_prompt=leader_prompt,
            expert_run_id=expert_run_id,
            stages=stages,
            prior_excerpt=discuss_text or discuss_err,
        )

    async def _leader_followup(
        self,
        *,
        session_id: str,
        leader_prompt: str,
        expert_run_id: str,
        stages: list[dict[str, Any]],
        prior_excerpt: str,
    ) -> dict[str, Any]:
        """One leader turn on the same session. Not another four-expert meeting."""
        leader_started = time.perf_counter()
        proc = await self._spawn(session_id, leader_prompt, timeout_s=self.leader_grace_s)
        pipes = _ChatPipes(proc)
        code = await pipes.wait(self.leader_grace_s)
        text, err = pipes.text()
        if code is None:
            await pipes.aclose()
            text, err, code = "", err, None
        stages.append(
            stage_record(
                "leader_decision",
                leader_started,
                ok=code == 0,
                leader_closed=True,
                same_process=False,
                returncode=code,
            )
        )
        package = self._try_package(text)
        if package is not None:
            return self._success(package, text, expert_run_id, stages)
        excerpt = (text or err or prior_excerpt or "")[:2000]
        logger.warning("leader decision missing: exit=%s excerpt=%s", code, excerpt[:500])
        return self._failure(
            error="leader_decision_timeout",
            expert_run_id=expert_run_id,
            backend="cli",
            stages=stages,
            raw_excerpt=excerpt or None,
        )

    async def _spawn(self, session_id: str, prompt: str, *, timeout_s: int) -> asyncio.subprocess.Process:
        return await asyncio.create_subprocess_exec(
            *self._command,
            "chat",
            "--mode",
            "team",
            "--session",
            session_id,
            "--json",
            "--timeout",
            str(timeout_s),
            prompt,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

    @staticmethod
    async def _pump(stream: Optional[asyncio.StreamReader], sink: bytearray) -> None:
        if stream is None:
            return
        while True:
            chunk = await stream.read(65536)
            if not chunk:
                return
            sink.extend(chunk)

    @staticmethod
    async def _send_leader_close(proc: asyncio.subprocess.Process, leader_prompt: str) -> None:
        if proc.stdin is None or proc.returncode is not None:
            return
        try:
            proc.stdin.write(leader_prompt.encode("utf-8") + b"\n")
            await proc.stdin.drain()
            proc.stdin.close()
            await proc.stdin.wait_closed()
        except (BrokenPipeError, ConnectionResetError, RuntimeError):
            logger.info("meeting process closed stdin before the leader handoff")

    @staticmethod
    async def _release(proc: asyncio.subprocess.Process) -> None:
        """Drop a chat that will not yield a decision, so the leader turn can use the channel."""
        if proc.returncode is not None:
            return
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()

    @staticmethod
    def _try_package(text: str):
        if not text.strip():
            return None
        try:
            return parse_technical_package(text)
        except (ValueError, Exception):  # noqa: BLE001
            logger.info("swarm output is not a technical package yet")
            return None

    def _success(
        self,
        package,
        text: str,
        expert_run_id: str,
        stages: list[dict[str, Any]],
    ) -> dict[str, Any]:
        parse_started = time.perf_counter()
        stages.append(stage_record("parse", parse_started, ok=True))
        return {
            "ok": True,
            "package": package.model_dump(mode="json"),
            "error": None,
            "expert_run_id": expert_run_id,
            "raw_excerpt": text[:2000],
            "backend": "cli",
            "review_required": package.readiness == "needs_human_review"
            or package.technical_approval_required,
            "stages": stages,
        }

    @staticmethod
    def _failure(
        *,
        error: str,
        expert_run_id: str,
        backend: str,
        stages: list[dict[str, Any]],
        raw_excerpt: Optional[str] = None,
    ) -> dict[str, Any]:
        return {
            "ok": False,
            "package": None,
            "error": error,
            "expert_run_id": expert_run_id,
            "raw_excerpt": raw_excerpt,
            "backend": backend,
            "review_required": True,
            "stages": stages,
        }
