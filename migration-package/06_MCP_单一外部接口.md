# HydroQuote 单一 MCP 对外接口设计

## 1. 外部服务形态

- 唯一 MCP endpoint：`/mcp`，Transport = **Streamable HTTP**，服务可在本地 `http://127.0.0.1:8001/mcp` 运行。
- 唯一 MCP Tool：`hydroquote_quote`；通过 `operation` 完成 `create`/`revise`/`get`/`submit_review`。
- 客户 Web 仍可使用原 FastAPI 兼容端点，但**必须委派给同一份 QuotationApplication**；不能在 REST 与 MCP 各写一遍计算逻辑。
- MCP v1 输入 JSON Schema：`contracts/hydroquote_quote_request.schema.json`；输出：`contracts/hydroquote_quote_response.schema.json`。
- 其他 Agent 若支持 MCP 可发现并调用；不支持 MCP 的 ERP/企业应用需要标准 MCP Client/Gateway，不能以普通 REST `POST /mcp` 代替 MCP 握手与工具调用。

## 2. 操作语义

| operation | 使用者 | 输入 | 正常返回 | 注意 |
|---|---|---|---|---|
| `create` | 已授权外部客户 | `project_text` 或 `parameters` | `quote_id`, `needs_input/processing/...` | 启动 LangGraph；不必同步等专家团队结束 |
| `revise` | 报价所属客户 | `quote_id` + 补参/修订 | 更新后状态 | 同一 thread_id 恢复，防止重复收费/PI |
| `get` | 报价所属客户 / 被授权内部 reviewer | `quote_id` | 进度、可公开技术摘要、商业价、PI 权限引用 | 角色字段过滤：Swarm 可读必要工况、不可读成本 |
| `submit_review` | **经过认证的人类审核动作** | `quote_id` + 决策与规则版本 | 审批状态更新 | Team 模型输出不可自己伪装审批 |

**注意**：路由 `fast_quote / expert_quote` 由系统内部规则自动生成，不接受客户端任意指定“绕开专家/人工复核”。

## 3. 公开状态与工作流进度

对外 `status`：`needs_input`, `preliminary`, `review_required`, `ready`, `rejected`, `error`。为了兼容先前 1.0 合同，新增可选展示字段：

- `workflow_path`: `fast_quote` 或 `expert_quote`（尚未路由时可 `null`）
- `workflow_stage`: `customer_inquiry`, `technical_selection`, `engineering_cost`, `commercial_quotation`, `pi_generation`, `completed` 等
- `expert_review_state`: `not_required`, `queued`, `running`, `validated`, `awaiting_human`, `failed`（内部实际状态应有审计）
- `inquiry_summary`: 已确认的净水头、设计流量、装机容量等经过脱敏的字段，仅对本项目拥有权限的请求显示

开发时建议将 `status=preliminary` 配合 `workflow_stage` 表示异步运行；`status=review_required` 表示人工需介入或专家通道已失败。不得在进行中提前返回伪 `ready`。

## 4. 外部接口绝不泄漏内部成本

客户可见：基本技术结果、五项客户报价行、报价总额、技术风险简述、报价/PI 文件权限链接。

客户不可见：`MainEquipmentBaseCost`、供应商采购价格、`InternalCost`、`RiskReserveRate`、利润/议价空间、内部 token、未批准的专家原始意见。允许内部审核身份读取**严格限定的技术字段**，而不是把全部内部成本塞进 MCP `get` 回包。

## 5. 鉴权与隔离

- TLS；生产使用 OAuth/Bearer 以及可信服务端身份映射，实际权限在 transport 与 application 层双重校验。
- `quote:create`, `quote:read`, `review:read`, `review:write` 区分；审核动作需**真实人类身份+单次审批授权**，不是 JiuwenSwarm 共享 token。
- `tenant_id` 从验证通过的 token 获取，绝不由入参声明；QuoteStore/文件下载都做 tenant check。
- `request_id` 幂等；创建与修订使用原子版本控制，防止重试重复产生订单或修改同一报价的金额。
- 限流、长度上限、文档解析防护、日志去敏、超时与取消、PI 短期签名链接。
- `request_id`, `trace_id`, `quote_id`, `rule_version` 足以关联日志，不需要写原始客户个人信息。

## 6. Python MCP Server 最小接口形态

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("HydroQuote")

@mcp.tool()
async def hydroquote_quote(
    schema_version: str,
    operation: str,
    request_id: str,
    quote_id: str | None = None,
    project_text: str | None = None,
    parameters: dict | None = None,
    revisions: dict | None = None,
    include_pi: bool = False,
    review: dict | None = None,
) -> dict:
    """MCP transport skeleton. Auth + schema + app service MUST be injected."""
    # Do NOT deploy this skeleton without real permission / schema checking.
    raise NotImplementedError
```

上述是**接口形态，不是可部署服务**。需由 Cursor 按官方 SDK 的受支持挂载方式实现 `/mcp`，并接入 `QuotationApplication`。应在启动时检查 `tools/list` 只有一个 Tool，且独立 client 能通过 MCP 协议（不是普通 HTTP POST）成功 `tools/call`。

## 7. Swarm 也通过同一个 MCP 入口取技术资料

复杂项目路由由 LangGraph 决定并启动内部 SwarmAdapter；JiuwenSwarm Team 使用授权的 `get` 读取对应 `quote_id` 工程参数。四专家返回的是 `TechnicalSelectionPackage`，Adapter 再交给 LangGraph 校验。**不要**让 JiuwenSwarm 的模型以 `submit_review` 自动批准自己生成的技术结果，也不允许 `get` 返回不属于此服务身份的客户数据。

## 8. 必须提供的接口测试

1. MCP 握手 / `tools/list`：仅一个 `hydroquote_quote`。
2. MCP `tools/call` create：标准项目返回 `quote_id` + 真实 Fast Quote 结果（同步或轮询）；缺项返回 `needs_input`。
3. Expert Quote：返回 `workflow_path=expert_quote`、进度，`get` 可查询；Team 实际完成后显示经过验证的技术包结果。
4. 第三方/越权 `get`：拒绝访问；未授权 `submit_review`：拒绝。
5. 报价重试幂等、Rule Version 稳定、不会重复生成 PI。
6. 不泄露内部成本、风险率、凭据。

## 9. 官方文档

- MCP：https://modelcontextprotocol.io/
- Python MCP SDK：https://github.com/modelcontextprotocol/python-sdk
- JiuwenSwarm MCP Client：https://github.com/openJiuwen-ai/jiuwenswarm/blob/develop/docs/en/MCPConfiguration.md
