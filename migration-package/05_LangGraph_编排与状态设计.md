# LangGraph 主编排技术规范

## 1. 唯一 Orchestrator 的工作范围

LangGraph 是完整 HydroQuote 报价工作流的唯一调度入口。它不实现水力公式、不自行计算价格；它决定何时调用 Agent Core、纯 Python 业务函数和 JiuwenSwarm，并管理状态、分支与人工确认。

主节点建议：

```text
START
  → intake
  → inquiry_agent_core
  → validate_inquiry
  → [needs_input → interrupt/resume] OR classify_complexity
  → [fast_quote] OR [expert_quote_jiuwenswarm]
  → merge_technical_package
  → validate_technical_package
  → [technical_human_gate if necessary]
  → engineering_cost_fanout [5 concurrent items]
  → engineering_cost_join
  → calculate_project_additional_cost
  → internal_cost_and_risk
  → [price_review_gate if any unresolved rule]
  → commercial_quotation
  → validate_pi_fields
  → [needs_input / human review when missing binding terms]
  → generate_pi
  → END
```

## 2. HydroQuoteState（建议字段）

```python
from typing import TypedDict, Literal

class HydroQuoteState(TypedDict, total=False):
    quote_id: str
    request_id: str
    tenant_id: str  # derived from auth, never client-authoritative
    status: str
    workflow_stage: str
    raw_input_ref: str
    inquiry: dict
    confirmed: bool
    missing_fields: list[str]
    conflict_flags: list[str]
    routing_path: Literal["fast_quote", "expert_quote"]
    routing_reasons: list[str]
    technical_package: dict
    expert_run_id: str
    expert_records: list[dict]
    equipment_costs: dict  # exactly five keyed entries after reducer
    project_additional_cost: str
    internal_cost: str
    commercial_quote: dict
    pi_artifact: dict
    rule_version: str
    warnings: list[str]
    human_review: dict
    trace_id: str
```

请用 Pydantic 验证跨服务模型；`TypedDict` 只是 LangGraph 结构提示。**不要把上传的整份客户文件、模型凭证、私密成本日志直接写进可能被外部查看的状态或 trace**。`thread_id` 与 `quote_id` 绑定并做 tenant check，避免其他客户复用 thread。

## 3. 条件路由代码形态（示意，需 Cursor 集成真实函数）

```python
from langgraph.graph import StateGraph, START, END

builder = StateGraph(HydroQuoteState)

builder.add_node("inquiry", inquiry_node)
builder.add_node("validate", validate_inquiry_node)
builder.add_node("fast_quote", fast_quote_node)
builder.add_node("expert_quote", expert_quote_jiuwenswarm_node)
builder.add_node("technical_validation", validate_technical_package_node)
builder.add_node("engineering_cost", engineering_cost_workflow_node)
builder.add_node("commercial", commercial_quotation_node)
builder.add_node("pi", pi_generation_node)

builder.add_edge(START, "inquiry")
builder.add_edge("inquiry", "validate")

# routing function must return one of: needs_input/fast_quote/expert_quote
builder.add_conditional_edges(
    "validate",
    route_after_inquiry,
    {
        "needs_input": END,  # return pending + resume on later customer update
        "fast_quote": "fast_quote",
        "expert_quote": "expert_quote",
    },
)
builder.add_edge("fast_quote", "technical_validation")
builder.add_edge("expert_quote", "technical_validation")
builder.add_edge("technical_validation", "engineering_cost")
builder.add_edge("engineering_cost", "commercial")
builder.add_edge("commercial", "pi")
builder.add_edge("pi", END)

# Add review/approval routing and durable checkpointer before production.
```

这只是 API 形态示意：完整实现必须将 `needs_input` 和技术/商业审核持久化成可继续的状态。对于外部 MCP 的长耗时请求，可以先立即返回 `quote_id,status`，再通过 `get` 查询进度，不应保持长连接直到专家团队完成。

## 4. Fast/Expert 路由如何保持可解释

设计 `route_after_inquiry(state)`: 首先 `missing_fields` 或关键冲突回 `needs_input`；否则从经确认的输入和版本化 `complexity_rules.yaml` 检查特殊工况、季节波动/泥沙/多个候选、控制要求、客户要求专家论证等。明确命中原因保存在 `routing_reasons`。模型可提供建议，但**最终路由由经审核的规则决定**。不能随手硬编码与业务源无关的工程阈值；需要业务审核的阈值留在 `RULES_DISCREPANCY_LOG.md`。

## 5. 五大设备核价必须并行且只计一次

选择两种可靠实现之一：

- **方案 A**：LangGraph `Send` 动态 fan-out，五个核价节点共享不可变 `technical_package`，独立计算对应设备，Reducer 汇总成以设备代码为 key 的字典；校验恰好五个唯一 key。
- **方案 B**：LangGraph 单一 `engineering_cost` 节点中通过 `asyncio.gather` 并行执行五个纯 Python 定价函数。对外依然保留这五个独立可测试的函数，记录每项计算 trace；如果定价函数是 CPU 小计算，`asyncio.gather` 不会让 CPU 运算本身加速，优势主要是结构清晰。

如果同一个重试节点重新执行，必须以 `quote_id + pricing_rule_version + equipment_type + calculation_revision` 幂等更新，而不是把单价再次累加。任一项失败或缺少核准定价公式，不得输出 `ready`。

## 6. Human-in-the-loop 和异常处理

- `needs_input`：向客户问缺项 → 持久化草稿 → 客户 revise 后从正确节点恢复，避免重新下单。
- `technical_review`：复杂 Swarm 技术包或矛盾项目需要工程师授权 → `interrupt` / resume。
- `pricing_review`：未知公式/价格带、未知风险率、超适用单机容量 → 人工确认规则版本后恢复。
- `pi_review`：供应商、付款、交付、保证条款未给全 → 禁止自动生成“已签发正式 PI”。
- `swarm_unavailable`、`tool_failed`、`timeout`：明确存入状态，若无完成结果只能 `review_required`，而非偷偷切 Fast Quote 成功。

`interrupt()` 依赖带持久化的 `checkpointer`；开发可使用内存检查点，正式部署必须使用具有持久化保证的后端。`Command(resume=...)` 的审核结果应由授权的后端来接收并验证，不能直接相信客户端宣称“approved”。

## 7. 三种状态区别

1. **LangGraph state/checkpoint**：业务路线、可恢复进度与计算结果的唯一全局状态。
2. **Agent Core Workflow Session**：某一次专业子工作流内部的执行上下文，不替代 LangGraph 的审批账本。
3. **JiuwenSwarm session**：复杂技术选型的专家协作执行上下文；通过 `quote_id` 关联并回传一个结构化技术包，不直接作为报价数据库。

单外部 MCP 的 `get` 返回公共子集和必要进度，不泄露内部详细成本或专家协作私密轨迹。

## 8. 基础测试数据

- Fast 示例：`H=50m`, `Q=6m³/s`, `installed=2400kW`, `units=2`, `unit=1200kW`, `50Hz`, `6300V`，容量与水力可行性仍需显式效率与配置校验。水轮机单项底价参考 `2×(50000+(1200-1000)×20)=108000 USD`，**不等于整张商业报价**。
- Expert 示例：确认已提供水头/流量/容量，但带有明显季节流量变化、较高泥沙或复杂的机组运行诉求，附人工审核的例外工况；要求四专家真实执行，结果经过校核。
- 缺项示例：只给 `2MW` 而没有 `Net Head`/`Design Flow`，应该进入 `needs_input`，**不启动 Swarm**。

## 9. 验收与官方文档

验收必须提供：StateGraph 节点 trace、路由原因、checkpointer resume、专家队列任务/失败回退、五项成本并行证据及准确合计。官方：https://docs.langchain.com/oss/python/langgraph/overview
