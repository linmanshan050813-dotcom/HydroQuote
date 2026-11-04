# openJiuwen Agent Core 使用纲要（HydroQuote · LangGraph 主编排版）

**定位**：这是使用与集成纲要，而非声称本地已运行成功的教程截图。官方 `develop` 文档与 pip 发行版可能存在接口差异，Cursor 必须先做兼容性测试并锁定版本。Agent Core 的作用是 **内部 Agent/Workflow 能力**，LangGraph 才是本项目的**全局状态与任务编排器**。

## 1. 四层能力的边界

| 组件 | 在 HydroQuote 的职责 | 主要接口 |
|---|---|---|
| LangGraph | Inquiry、Fast/Expert 路由、Eng Cost、Commercial、PI、持久化与审核 | `StateGraph`, conditional edges, `interrupt`, checkpointer |
| openJiuwen Agent Core | Customer Inquiry 提取/追问、Fast Quote 技术说明、报价说明/PI 文字生成 | `Workflow`, `WorkflowAgent`, `LLMComponent`, `QuestionerComponent`, `ToolComponent`, Session |
| JiuwenSwarm | 复杂技术选型的四专家团队合作 | Team/Cluster mode、CLI `--mode team`、A2A Gateway（经验证） |
| MCP | 完整报价的统一第三方调用入口 | `tools/list`, `tools/call`, `FastMCP`, Streamable HTTP |

**不要**让 Agent Core 自己安排整个五阶段报价，随后再由 LangGraph 安排同一件事；会形成双重编排，状态可能分叉。每个 Agent Core Workflow 只完成明确的子任务，将结果返回 LangGraph 的状态对象。

## 2. 安装与依赖

建议：Python 3.11 虚拟环境作为业务后端，JiuwenSwarm 单独环境（防止依赖冲突）。具体支持版本要以当次 PyPI 和仓库为准。

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install openjiuwen langgraph 'mcp[cli]' fastapi uvicorn pydantic
python -c "import openjiuwen, langgraph, mcp; print('basic imports OK')"
```

安装后用 `pip freeze` 锁定经过测试的版本；不要直接在生产环境使用无版本上下限的依赖。JiuwenSwarm 的 PyPI 包当前为 `workswarm`，CLI 命令仍带 `jiuwenswarm` 前缀。**不要把 `JiuwenSwarm` 想象成 `openjiuwen.core` 下面的某个类。**

## 3. Agent Core 常用对象

| 对象 | 用途 | HydroQuote 对应 |
|---|---|---|
| `Workflow` | 定义含 start/end/组件/边的子工作流 | Inquiry、Fast Selection、Quotation Description |
| `WorkflowAgent` | 将 Workflow 封装为可调用 Agent | `EngineeringAgent`、`QuotationAgent` |
| `WorkflowCard` | 子流程 id/name/version | 版本与追踪 |
| `Start`, `End` | 输入输出节点 | 统一 Pydantic 结构 |
| `LLMComponent` | 模型理解或解释 | 从项目书抽取候选参数、技术说明 |
| `QuestionerComponent` | 缺项追问/收集字段 | 客户 Inquiry Confirmation |
| `ToolComponent` | 绑定工具函数/外部 API | 校验、转换、纯 Python 工程规则 |
| `MCPTool`, `StreamableHttpClient` | 作为 MCP Client 使用外部工具 | 用于独立互操作测试，**主业务不要自己 MCP 调自己** |
| `create_workflow_session` | 单次子工作流上下文 | 每次调用独立 session；主业务状态由 LangGraph 管 |

## 4. 最小 Workflow 示例（官方接口形态）

这段代码只演示 **Graph 的语法与 Session**，不包含模型调用；不同版本的 `End` 构造参数需以实测为准。

```python
import asyncio
from openjiuwen.core.workflow import Workflow, Start, End, create_workflow_session

flow = Workflow()
flow.set_start_comp("start", Start(), inputs_schema={"query": "${query}"})
flow.set_end_comp(
    "end",
    End({"response_template": "{{result}}"}),
    inputs_schema={"result": "${start.query}"},
)
flow.add_connection("start", "end")

async def smoke_test():
    result = await flow.invoke(
        {"query": "HydroQuote inquiry"},
        create_workflow_session(),
    )
    print(result)

asyncio.run(smoke_test())
```

真实 WorkflowAgent 需要 `WorkflowAgentConfig`, `WorkflowAgent`（官方文档路径 `openjiuwen.core.application.workflow_agent`）并通过 `add_workflows([flow])` 绑定，实际 `invoke()` 的输入格式与输出对象必须对照所安装版本验证。

## 5. 两个真实 Agent Core Agent：具体如何实现

### EngineeringAgent

- 子流 A：`inquiry_extract`：LLM 提取 `project_name/country/location/net_head_m/design_flow_m3s/installed_capacity_kw/voltage/frequency/units`，保留字段证据（来源段落/置信提示）。
- 子流 B：`inquiry_confirm`：`QuestionerComponent` 或 LangGraph 审核/追问节点执行缺项确认。LLM 不能擅自补齐关键工程值。
- 子流 C：`fast_selection`：用 `ToolComponent` 或代码节点调用 **纯 Python 规则函数**，得到一个候选机型、机组配置、五设备清单；LLM 只解释规则决策。
- 结果需符合 `TechnicalSelectionPackage`：实际 Rule Path 也不得绕过 Schema/水力校核。

### QuotationAgent

- 主要用途是整理来自已经计算完毕的确定性业务结果，生成可读技术说明、客户版本商业条款描述和 PI 文字字段。
- **不要**通过 LLM 生成人工成本或任意调整 ×2.40。
- `engineering_cost`、`commercial_quotation`、`pi_generation` 是 **LangGraph 的独立业务节点**；必要时在其中调用 QuotationAgent 的局部 Workflow，而不是再执行一个完整的重复报价流程。

## 6. 与 LangGraph 的实际对接

每个 Agent Core 功能提供清晰的 Python Adapter，例如：

```python
class InquiryAgentAdapter:
    def __init__(self, agent):
        self.agent = agent

    async def extract(self, raw_text: str) -> dict:
        # Adapt the exact openJiuwen invoke schema for the pinned version.
        result = await self.agent.invoke({"query": raw_text, "conversation_id": "per-request"})
        return validate_inquiry_result(result)  # Pydantic validation (implement)
```

`validate_inquiry_result` 是项目自定义函数，示例展示 Adapter 约束，**并非可复制即运行的完整实现**。实际实现应创建**每份询盘唯一的 conversation/session id**，不能使用上面演示字符串。LangGraph 节点调用 Adapter，写回 `HydroQuoteState`。缺参由 LangGraph 结束/中断并等待客户补齐。Swarm 只接收确认后的输入。

### `Questioner` 与 LangGraph `interrupt` 如何分工？

- Agent Core `QuestionerComponent` 负责决定**应该问客户什么**、辅助解释字段。
- LangGraph `interrupt()` 和 checkpointer 负责**业务暂停与恢复**，同一 `thread_id` 恢复流程；不能依赖单次 Agent Core session 作为整个报价的持久化账本。
- 多轮补参回写结构化字段后再校验，校验通过才执行 Fast/Expert 路由。

## 7. MCP：对外 Server 与 Agent Core Client 的区别

**对外 Server** 用官方 `mcp` Python SDK 的 `FastMCP`，对外只有一个工具：

```python
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("HydroQuote")

@mcp.tool()
def hydroquote_quote(operation: str, request_id: str, schema_version: str = "1.0") -> dict:
    """Public integration skeleton only; implementation must validate full contract and auth."""
    raise NotImplementedError("Delegate to QuotationApplication")
```

这是**最小 API 外形演示**，它没有完成合同参数、认证、Streamable HTTP 挂载或多租户限制，绝不能当作生产可用代码。真机测试必须从独立 MCP Client 执行 `list_tools` 和 `call_tool`。

**对内 MCP Client**：官方 `MCPTool` + `StreamableHttpClient` 可连接别人的 MCP 服务，但本项目的 Fast Quote/COST 引擎在同代码仓库内，应该直接调用纯 Python 函数，**不要把自己的 MCP 出口绕回自己的入口**。

## 8. 结构化状态与校验

LLM 抽取的原始单位、归一化值、字段来源、冲突应保留在 `Inquiry` Pydantic 对象。`TechnicalSelectionPackage` 是 Fast/Expert 都必须返回的统一合同。核心要点：

- `Net Head` 必须明确是净水头；若只给毛水头必须确认。
- `Power kW = 9.81 × Q(m³/s) × H(m) × η` 用于物理校核；效率若未知须显式标注假设并影响 `quotation_readiness`。
- 设备清单必须恰好含 Hydro Turbine、Generator and Exciter/AVR、Speed Governor、Inlet Valve、Automation System。
- 模型不能自行产生最终工程安全结论。异常/不完整时进入 review/human gate。

## 9. 学习与验证顺序

1. 先运行 `Workflow(Start → End)`。
2. 构建真实 `EngineeringAgent`，跑项目书字段提取和 `QuestionerComponent`。
3. 构建 `fast_selection` 与实际 Python 规则工具绑定。
4. 将上述两个子流包进 LangGraph 节点；证明全局 `thread_id` 能暂停和恢复。
5. 构建 `QuotationAgent` 的技术/商业说明组件，禁止修改成本计算结果。
6. 让 Expert Quote 调用 JiuwenSwarm Adapter，产出同一种 `TechnicalSelectionPackage`。
7. 端到端调通独立 MCP Client、正常 Fast Quote、复杂 Expert Quote 与 PI。

**通过判据**：运行日志中必须能看到 LangGraph 对真实 `WorkflowAgent.invoke` 的调用、结构化状态更新与可核验的下游业务结果；装依赖或写 mock 类不能当成验收完成。

## 10. 官方参考

- Agent Core：https://github.com/openJiuwen-ai/agent-core
- Workflow 构建：https://github.com/openJiuwen-ai/agent-core/blob/develop/docs/en/2.Development%20Guide/Workflows/Build%20Workflow.md
- WorkflowAgent：https://github.com/openJiuwen-ai/agent-core/blob/develop/docs/en/2.Development%20Guide/Agents/Building%20WorkflowAgent.md
- Custom Tools / MCPTool：https://github.com/openJiuwen-ai/agent-core/blob/develop/docs/en/2.Development%20Guide/Basic%20Functions/Custom%20Tools.md
- LangGraph：https://docs.langchain.com/oss/python/langgraph/overview
