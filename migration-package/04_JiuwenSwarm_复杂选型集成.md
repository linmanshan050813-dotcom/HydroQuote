# JiuwenSwarm：HydroQuote Expert Quote 分支集成说明

## 1. 精确定位

JiuwenSwarm 仅运行于 **LangGraph 的 `expert_quote` 节点**，任务是复杂工程项目的 **技术选型**。标准项目走 Fast Quote，不启动 Swarm。Swarm 在成本核算之前产出 `TechnicalSelectionPackage`；它不负责修改价格、签发商业报价或代替人类审批。

## 2. 团队角色和处理次序

| 成员 | 独立任务 | 交叉审核重点 |
|---|---|---|
| `Hydraulic Expert` | 净水头、设计流量、功率与效率假设、机型适用性 | 水力矛盾和严重不确定性 |
| `Equipment Expert` | 水轮机型式、机组数量及单机容量、五项主设备配置 | 设备可制造性、控制/阀门接口 |
| `Operations Expert` | 枯水期、负荷变化、检修冗余、控制策略与运行灵活性 | 极端流量与部分负荷运行风险 |
| `Risk Reviewer` | 冲突、缺项、风险、不同专家分歧、需人工确认的条件 | 不经审核不能下结论 |
| `Swarm Leader` | 发独立任务、推进讨论、组织交叉审查、合并输出 | 检查四专家均真实参加，而不是替他们编意见 |

**必须执行**：`独立分析（先互不可见） → 专家讨论 → 交叉审核 → Leader 合成一份 TechnicalSelectionPackage`。报告保留 4 份专家意见、争议与结论、假设、风险、是否需要人工审批。LLM 结论不可绕过规则校验。

## 3. 入口与输入

LangGraph 在进入专家节点前必须持有：

- `quote_id`, `tenant_id`（后者由可信身份映射，不是客户自己声明）
- 确认的 `Inquiry` 结构化参数（不含额外客户个人信息）
- `routing_reasons`, `engineering_rules_version`, `source_provenance`
- 是否提供流量历时曲线、含沙量等可补充数据，以及已标记的冲突

**缺少净水头或设计流量**时回 `needs_input`，不准让专家编造。发给 Team 的字段需脱敏。Swarm 可以用受限 MCP token 调用同一个 `hydroquote_quote(operation='get')` 查阅技术字段；MCP public response 不显示原始内部成本。

## 4. 输出合同：TechnicalSelectionPackage

严格遵照 `contracts/technical_selection_package.schema.json`。一个最终方案含：

- `recommended_turbine_type`：仅一个主推机型；可有备选方案与权衡说明。
- `unit_configuration`：机组数量、单机容量（以及必要备选）。
- `hydraulic_check`：Q/H/P、效率来源或假设、与装机容量的一致性结论。
- `equipment_scope`：五大主设备、Automation 范围、可选升级列表。
- `expert_opinions`：四份明确归属的独立分析。
- `discussion_summary`, `cross_review`, `assumptions`, `risk_notes`, `source_provenance`。
- `readiness`：`preliminary_ready` / `firm_ready` / `needs_human_review`。

此包通过 `Pydantic / JSON Schema`、物理校核及定版配置校核后才能进入 LangGraph Engineering Cost。专家互相同意不意味着数值正确：仍以 Python 验证结果为准。

## 5. 可靠的集成方式

### 方案 A：本地真实 PoC（推荐先做）

官方 CLI 文档提供：

```powershell
# JiuwenSwarm 使用独立 Python 环境安装并初始化
pip install workswarm
jiuwenswarm-init
jiuwenswarm-start app

# 从另一个终端调用真正的 Team mode
jiuwenswarm chat --mode team --session hydroquote-demo-001 --json --timeout 300 "Review HydroQuote complex inquiry quote_id=QUOTE-EXAMPLE-001; use connected MCP get to read allowed technical data; have four experts independently analyze, discuss, cross-review and return only TechnicalSelectionPackage JSON."
```

安装后应以 `jiuwenswarm chat --help`/当前 release 验证命令；网络端口/环境以启动日志为准。**CLI 使用 Gateway `/tui` WebSocket 通道，并且与同一实例 TUI 可能互相顶替连接**，所以用 `SwarmAdapter` 的任务队列串行运行（同时只允许 1 个此通道 Team 调用）。进程由 `asyncio.create_subprocess_exec` 启动、参数列传递，禁止 `shell=True` 拼接客户原文；用已净化的固定模板 + `quote_id`，加入 timeout、取消和日志脱敏。`--json` stdout 中的响应还需 JSON 解包与二次 schema 校验，不要相信模型一定只输出 JSON。

### 方案 B：生产环境候选

官方提供 JiuwenSwarm **A2A Gateway**，可探索从 LangGraph `SwarmAdapter` 使用受认证 A2A Client 访问独立服务。**不得在未核验版本、并发、身份隔离、Team mode 可控性和回传 Schema 前宣称 A2A 自动团队服务已实现。** 如官方接口不满足，保留队列/人工审核回退，并在 `MIGRATION_REPORT.md` 写清实现边界。

### 接入 MCP 的独立一份配置

将以下片段合并到 `~/.jiuwenswarm/config/config.yaml`，使用有限权限的内部服务身份，密钥由环境/安全存储注入，配置文件不存真实密钥。

```yaml
mcp:
  servers:
    - name: hydroquote
      enabled: true
      transport: streamable-http
      url: http://127.0.0.1:8001/mcp
      timeout_s: 60
      # Authentication headers must be injected securely at runtime.
```

运行 ` /mcp list` 查工具是否连接，并核对工具列表只含 `hydroquote_quote`。Team 只有 `get` 技术资料权限；禁止 `submit_review`、修改规则、调用任何不属于该 Team 任务的报价 ID。

## 6. 防循环、防伪造、防越权

- Swarm→MCP `get` 是只读获取专家输入；不得通过同一工具的 `create/revise` 触发再次进入 Expert Quote，避免循环。
- LangGraph 创建 Expert Review task，SwarmAdapter 读取它、返回结果，图负责审核并继续执行。
- 成本核价在 Expert Quote 完成之后统一运行一次，不允许专家在内部随意提交一个“最终报价”。
- Swarm 输出 JSON 不合法、任何专家意见缺失、运行超时、缺来源时必须 `review_required`，不能自动降级成假装正常的 Fast Quote。
- 人工审批采用 LangGraph checkpointer + `interrupt` / `resume`；Service token 不代替审批人的身份。
- 高并发需队列和隔离；同一个 CLI 连接不能承诺多租户生产并发能力。

## 7. 演示必须提供什么证据

1. `jiuwenswarm --version` 或真实包版本、Team CLI 可用截图/输出。
2. 独立 `Hydraulic Expert`, `Equipment Expert`, `Operations Expert`, `Risk Reviewer` 的真实任务记录，不是 Leader 模拟四人。
3. MCP `get` 真实工具调用，request_id/quote_id 与 audit trail 可以关联。
4. 独立分析、讨论、交叉审核的记录。
5. LangGraph 把结果写成 `TechnicalSelectionPackage`，校验通过后进入五设备核价；失败时进入 `review_required`。
6. 一个 **Fast Quote** 例子证实没有调 JiuwenSwarm。

**官方文档**：
- Team：https://github.com/openJiuwen-ai/jiuwenswarm/blob/develop/docs/en/AgentTeam.md
- CLI：https://github.com/openJiuwen-ai/jiuwenswarm/blob/develop/docs/en/CLI.md
- MCP：https://github.com/openJiuwen-ai/jiuwenswarm/blob/develop/docs/en/MCPConfiguration.md
- A2A：https://github.com/openJiuwen-ai/jiuwenswarm/blob/develop/docs/en/A2A.md
