"""Wall-clock spans and why a HydroQuote request waited.

JiuwenSwarm team mode is one subprocess: four experts analyze, then discuss,
cross-review, then the leader synthesizes. Those rounds run one after another.
A process-wide lock also admits only one team chat at a time, because the CLI
shares a single gateway channel. `attribute_wait` names the span that held the
clock instead of blaming "swarm" as a whole.
"""

from __future__ import annotations

import time
from typing import Any

# Request is "slow" when the summed leaf spans reach this many milliseconds.
DEFAULT_SLOW_MS = 5000.0

CAUSE_DETAIL: dict[str, str] = {
    "not_slow": "整单墙钟没有超过慢阈值，没有单一环节把请求拖住。",
    "serial_cli_queue": (
        "本单在等全局队列。jiuwenswarm 的 team 通道同一时刻只允许一个调用，"
        "前一单没结束就会堵在 SwarmAdapter 的锁上。这段时间还没开始专家讨论。"
    ),
    "cli_cold_start": (
        "时间主要花在拉起 jiuwenswarm 进程（解释器、读配置、连接 MCP），"
        "专家讨论还没开始。"
    ),
    "team_sequential_rounds": (
        "时间主要花在 team 子进程内部。四位专家先独立分析，再讨论、交叉审核，"
        "最后由 leader 合成一份 JSON。这些轮次在同一次 CLI 调用里串行，"
        "墙钟约等于各轮之和，不会因为用了 swarm 而并行变短。"
    ),
    "leader_close": (
        "讨论时限到了，会议进程没有被杀掉。同一场会话交给组长，由组长给出技术方案。"
    ),
    "leader_unresolved": (
        "讨论结束后已经交给组长，但组长没有交出方案。不会因此再自动重开一整场专家会。"
    ),
    "swarm_timeout": (
        "组长拍板阶段结束时子进程仍无方案，才停止该次调用。讨论时限本身不会把整场会议杀掉。"
    ),
    "output_parse": "CLI 已经返回，时间主要花在从 stdout 抽出 TechnicalSelectionPackage。",
    "inquiry_llm": (
        "时间主要花在询价抽取的 LLM。IBM 路径要先换 IAM token 再生成；"
        "这条路径不经过 swarm。"
    ),
    "llm_provider_fallback": (
        "询价 LLM 的前序供应商失败后才落到后面的供应商，"
        "等待时间是多次请求（含各自超时）相加。默认顺序是 ibm → openai → deepseek。"
    ),
    "swarm_unavailable": (
        "路由进了专家路径，但 jiuwenswarm 不可用，适配器立刻返回。"
        "如果体感仍然慢，看别的环节，不是 team 在跑。"
    ),
    "fast_quote": "走的是规则快选，没有启动四专家 team。",
    "validate_inquiry": "时间主要花在询价字段校验，这是本地规则，不调用 swarm。",
    "route_decision": "时间主要花在快选/专家路由判断，这是本地规则。",
    "technical_validation": "时间主要花在技术包和水力校核，这是本地规则。",
    "engineering_cost": "时间主要花在五项设备成本核算。",
    "commercial": "时间主要花在商务描述。",
    "pi_document": "时间主要花在生成 PI 文档。",
}

_NODE_CAUSE = {
    "inquiry": "inquiry_llm",
    "validate": "validate_inquiry",
    "annotate_route": "route_decision",
    "fast_quote": "fast_quote",
    "expert_quote": "team_sequential_rounds",
    "technical_validation": "technical_validation",
    "engineering_cost": "engineering_cost",
    "commercial": "commercial",
    "pi": "pi_document",
}

_SWARM_STAGE_CAUSE = {
    "queue_wait": "serial_cli_queue",
    "process_spawn": "cli_cold_start",
    "cli_wall": "team_sequential_rounds",
    "leader_decision": "leader_close",
    "parse": "output_parse",
}


def elapsed_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 1)


def stage_record(name: str, start: float, **extra: Any) -> dict[str, Any]:
    """One finished span. `start` is a `time.perf_counter()` value."""
    return {"stage": name, "elapsed_ms": elapsed_ms(start), **extra}


def cause_of(stage: dict[str, Any]) -> str:
    """Stable cause code for one leaf span."""
    if stage.get("error") == "leader_decision_timeout":
        return "leader_unresolved"
    if stage.get("timed_out") or stage.get("error") == "swarm_timeout":
        return "swarm_timeout"
    name = str(stage.get("stage") or "")
    if name == "availability_check":
        if stage.get("available") is False:
            return "swarm_unavailable"
        return "not_slow"
    if name == "inquiry":
        attempts = stage.get("llm_attempts") or []
        if any(not item.get("ok", True) for item in attempts):
            return "llm_provider_fallback"
        return "inquiry_llm"
    if name in _SWARM_STAGE_CAUSE:
        return _SWARM_STAGE_CAUSE[name]
    if name in _NODE_CAUSE:
        return _NODE_CAUSE[name]
    return "not_slow"


def _leaves(trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Prefer swarm sub-spans so the parent expert node is not counted twice."""
    leaves: list[dict[str, Any]] = []
    for event in trace:
        nested = event.get("stages")
        if isinstance(nested, list) and nested:
            for stage in nested:
                if isinstance(stage, dict) and "elapsed_ms" in stage:
                    leaves.append(dict(stage))
            continue
        if "elapsed_ms" not in event:
            continue
        leaves.append(
            {
                "stage": event.get("node") or event.get("event"),
                "elapsed_ms": event["elapsed_ms"],
                "event": event.get("event"),
                "llm_attempts": event.get("llm_attempts"),
                "error": event.get("error"),
            }
        )
    return leaves


def attribute_wait(
    trace: list[dict[str, Any]] | None,
    *,
    slow_ms: float = DEFAULT_SLOW_MS,
) -> dict[str, Any]:
    """Name the span that accounts for a long wait.

    Leaf spans are graph nodes, except `expert_quote`, which is replaced by
    the adapter spans (`queue_wait`, `process_spawn`, `cli_wall`, `parse`).
    The request cause is `not_slow` until the summed leaves reach `slow_ms`.
    Each stage still carries its own cause so a fast run can be inspected too.
    """
    leaves = _leaves(list(trace or []))
    annotated: list[dict[str, Any]] = []
    for item in leaves:
        cause = cause_of(item)
        annotated.append(
            {
                **item,
                "cause": cause,
                "cause_detail": CAUSE_DETAIL[cause],
            }
        )
    ranked = sorted(annotated, key=lambda item: float(item["elapsed_ms"]), reverse=True)
    total = round(sum(float(item["elapsed_ms"]) for item in ranked), 1)
    dominant = ranked[0] if ranked else None
    slow = total >= slow_ms and dominant is not None
    cause = cause_of(dominant) if slow and dominant is not None else "not_slow"
    share = 0.0
    if dominant is not None and total > 0:
        share = round(float(dominant["elapsed_ms"]) / total, 3)
    return {
        "total_ms": total,
        "slow": slow,
        "slow_ms": slow_ms,
        "dominant_stage": None if dominant is None else dominant.get("stage"),
        "dominant_ms": 0 if dominant is None else dominant.get("elapsed_ms"),
        "share": share,
        "cause": cause,
        "cause_detail": CAUSE_DETAIL[cause],
        "stages": ranked,
    }
