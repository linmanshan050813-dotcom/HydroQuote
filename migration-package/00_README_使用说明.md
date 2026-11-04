# HydroQuote AI · LangGraph + JiuwenSwarm + openJiuwen Agent Core + 单一 MCP

版本：v2.0（2026-11-03）。**这是更新后的实施文件包，并非代码已经完成重构。**

## 当前确定的架构（覆盖旧版方案）

- **LangGraph Orchestrator 是唯一全局业务编排器**：管理 Inquiry → Fast/Expert 技术选型 → Engineering Cost → Commercial Quotation → PI，负责可恢复状态、条件分流、人工审核与失败重试。
- **Customer Inquiry**：用 Agent Core 的 Agent + Workflow 完成文档提取、参数核对、缺失追问与用户确认。
- **Fast Quote**：标准项目调用确定性 Python 规则引擎；Agent Core 可承担专业子工作流，但不争夺全局调度权。
- **Expert Quote**：仅复杂项目进入 **JiuwenSwarm Team**，由 Hydraulic Expert、Equipment Expert、Operations Expert、Risk Reviewer 独立分析、讨论、交叉审核，输出结构化 Technical Selection Package。
- **统一技术方案校核**：Fast 和 Expert 汇入同一套 Schema/水力校核/人工审批条件；没有任何专家可以绕过定价规则。
- **Engineering Cost**：五大主设备核价并行执行；完成后核算附加成本、风险预留和内部成本。
- **Commercial Quotation**：执行原有 ×2.40 规则，不由 LLM 自行算钱。
- **PI Generation**：模板填充、字段与金额校验、受权文件生成。
- **对外仅一个 MCP Server（`/mcp`）和一个 MCP Tool（`hydroquote_quote`）**：其他 Agent/企业 MCP Client 通过统一入口调用完整报价，不暴露内部工具和内部成本。
- **开发执行者只有 Cursor Agent**：在 Cursor 中加载整个仓库并按阶段改写、测试、报告。无需另一个 Agent 来指挥 Cursor。

## 文件索引

| 文件 | 用途 |
|---|---|
| `01_HydroQuote_完整重构方案.md` | 新版总体架构、业务规则、系统边界、阶段实施 |
| `02_OpenJiuwen_Agent_Core_使用纲要.md` | Agent Core 核心 API、如何与 LangGraph 分工、示例 |
| `03_Cursor_Agent_实施总指令.md` | 可一次粘贴到 **Cursor Agent** 的开发任务说明 |
| `04_JiuwenSwarm_复杂选型集成.md` | 4 专家团队、Team CLI/A2A Adapter、数据契约与审核 |
| `05_LangGraph_编排与状态设计.md` | StateGraph、Fast/Expert 路由、并行核价、持久化、伪代码 |
| `06_MCP_单一外部接口.md` | 一个 MCP 工具的操作、权限、请求/响应契约 |
| `07_验收测试矩阵.md` | 六阶段交付、演示场景、通过判据 |
| `architecture/HydroQuote_Workflow.mmd` | 与用户指定步骤一致的 Mermaid 架构流程图 |
| `contracts/*` | MCP 请求/响应与内部技术选型包 JSON Schema、样例 |

## 直接开始（Windows / Cursor）

1. 打开现有 HydroQuote **仓库根目录**，新建功能分支 `feature/langgraph-jiuwenswarm-mcp`。
2. 将本包解压到仓库下 `migration-package/`，不要上传任何真实 API Key、账号密码或私有客户项目书。
3. 在 Cursor 打开 **Agent 模式**，复制 `03_Cursor_Agent_实施总指令.md` 全文执行。允许 Cursor 修改代码并运行本地测试；禁止未经授权 push、merge 或生产部署。
4. 第一轮要求 Cursor 给出 `docs/BASELINE_AUDIT.md` 和 LangGraph/OpenJiuwen/Swarm 兼容性检查，再按各阶段持续落地。
5. 关键运行证据：标准 Fast Quote、真正的 JiuwenSwarm Expert Quote、五设备并行计算、单 MCP Client 调用、PI 下载、缺参/审批暂停与恢复。

> 旧任务包中“Agent Core 全局主编排”和“Swarm 仅做报价完成后的复核”已废弃。**本包中 Swarm 是复杂技术选型分支的一部分，必须在进入成本核算前完成；LangGraph 是唯一业务主编排器。**

## 参考

- HydroQuote：https://github.com/linmanshan050813-dotcom/HydroQuote
- LangGraph：https://docs.langchain.com/oss/python/langgraph/overview
- openJiuwen Agent Core：https://github.com/openJiuwen-ai/agent-core
- JiuwenSwarm：https://github.com/openJiuwen-ai/jiuwenswarm
- JiuwenSwarm CLI：https://github.com/openJiuwen-ai/jiuwenswarm/blob/develop/docs/en/CLI.md
- JiuwenSwarm MCP：https://github.com/openJiuwen-ai/jiuwenswarm/blob/develop/docs/en/MCPConfiguration.md
- MCP Python SDK：https://github.com/modelcontextprotocol/python-sdk
