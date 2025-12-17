# DeepSOC 项目审查与优化报告 (2025)

**日期**: 2025-12-17
**审查人**: AI Assistant

## 1. 项目概览与回顾
DeepSOC 是一个基于多智能体（Multi-Agent）架构的安全运营中心自动化系统。项目启动于半年前，核心架构采用了 Flask + SQLAlchemy + RabbitMQ + OpenAI 的经典组合。

经过对代码库的深度审查，我们发现该项目架构清晰，角色分工明确（Captain, Manager, Operator, Executor, Expert），符合当前 Agentic Workflow 的设计理念。然而，随着 LLM 技术的快速迭代（如 OpenAI Structured Outputs, MCP 协议的普及）以及前端设计美学的演进，项目存在一定的技术债和用户体验优化空间。

## 2. 行业最新动向与技术趋势对比

| 特性 | 当前项目实现 | 行业最新趋势 | 差距与建议 |
| :--- | :--- | :--- | :--- |
| **LLM 交互** | 文本/YAML 提示词工程 | **Structured Outputs (JSON Schema)** | 严重。目前依赖 LLM 输出 YAML 并正则解析，极其脆弱。建议全面迁移至 OpenAI SDK 的 `response_format` 或 Pydantic 模型验证。 |
| **工具调用** | 自定义 Plugin/Playbook | **Model Context Protocol (MCP)** | 中等。项目提及 MCP 但未标准化。建议采用标准 MCP 协议连接外部安全工具，提高通用性。 |
| **任务编排** | 轮询数据库 (Polling) | **Event-Driven / Async** | 中等。Agent 采用 `while True` 轮询。建议改为纯事件驱动（RabbitMQ Consumer 触发 Agent 动作）。 |
| **界面风格** | 早期 Bootstrap, 原色高亮, AI味重 | **Neo-Brutalism / Bento Grid / Clean Dark** | 严重。当前 Warroom 界面颜色杂乱，难以长期使用。建议进行彻底的 UI/UX 升级。 |

## 3. 优化规划 (Roadmap)

### 3.1 核心架构升级 (Backend)
- **MCP 标准化集成 (SOAR as MCP Server)**:
    - 鉴于开源项目 `soar-mcp` 已实现将 SOAR 剧本直接转换为 MCP Resources/Tools，DeepSOC 应全面转型为 **MCP Client**。
    - **弃用 Playbook Prompts**: 不再需要在 Prompt 中硬编码或 RAG 检索 Playbook 列表。
    - **动态工具发现**: Agent (如 Manager/Operator) 启动时连接 SOAR MCP Server，动态获取当前可用工具列表，直接通过 LLM Function Calling 调用。
- **结构化输出迁移**: 逐步引入 Pydantic 模型，利用 LLM 原生的结构化输出能力替代不稳定的 YAML 解析。

### 3.2 界面与体验升级 (Frontend UI/UX)
针对当前 Warroom 界面设计风格的问题，我们计划引入全新的设计语言：

- **设计目标**: 摒弃过度装饰和高饱和度配色，探索更具创新性和清爽感的视觉风格。
- **Warroom 交互优化**:
    - **Timeline/Chat Stream**: 将原本杂乱的角色对话改为清晰的时间轴或聊天流视图。
    - **角色区分**: 优化角色识别机制，避免依赖大面积文字颜色高亮。
    - **可视化增强**: 引入 ECharts 或 Recharts 绘制攻击链路图、威胁评分仪表盘，替代纯文本展示。

### 3.3 长期规划
- **多 MCP Server 协同**: 连接 CMDB, Threat Intelligence 等其他 MCP Server，构建完整的安全工具生态。
- **LLM 可观测性**: 接入 LangFuse 或 Arize 追踪 Token 消耗和 Trace。

## 4. 总结
DeepSOC 的基础架构是稳固的。接下来的重点是 **"Backend 做减法 (通过 MCP)"** 和 **"Frontend 做加法 (UI/UX 升级)"**。通过引入 MCP 协议，我们可以卸下维护 Playbook 适配层的重担；通过现代化的 UI 设计，我们将把 DeepSOC 从一个"实验性 Demo" 升级为"企业级产品"。
