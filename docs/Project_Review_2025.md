# DeepSOC 项目审查与优化报告 (2025)

**日期**: 2025-12-17
**审查人**: AI Assistant

## 1. 项目概览与回顾
DeepSOC 是一个基于多智能体（Multi-Agent）架构的安全运营中心自动化系统。项目启动于半年前，核心架构采用了 Flask + SQLAlchemy + RabbitMQ + OpenAI 的经典组合。

经过对代码库的深度审查，我们发现该项目架构清晰，角色分工明确（Captain, Manager, Operator, Executor, Expert），符合当前 Agentic Workflow 的设计理念。然而，随着 LLM 技术的快速迭代（如 OpenAI Structured Outputs, MCP 协议的普及），项目存在一定的技术债和优化空间。

## 2. 行业最新动向与技术趋势对比

| 特性 | 当前项目实现 | 行业最新趋势 | 差距与建议 |
| :--- | :--- | :--- | :--- |
| **LLM 交互** | 文本/YAML 提示词工程 | **Structured Outputs (JSON Schema)** | 严重。目前依赖 LLM 输出 YAML 并正则解析，极其脆弱。建议全面迁移至 OpenAI SDK 的 `response_format` 或 Pydantic 模型验证。 |
| **工具调用** | 自定义 Plugin/Playbook | **Model Context Protocol (MCP)** | 中等。项目提及 MCP 但未标准化。建议采用标准 MCP 协议连接外部安全工具，提高通用性。 |
| **上下文管理** | 简单的字符串拼接 | **RAG (Vector DB) & Long Context** | 中等。随着 Playbook 增多，Prompt 会溢出。建议引入向量数据库（如 Chroma/Qdrant）检索相关 Playbook。 |
| **任务编排** | 轮询数据库 (Polling) | **Event-Driven / Async** | 中等。Agent 采用 `while True` 轮询。建议改为纯事件驱动（RabbitMQ Consumer 触发 Agent 动作）。 |
| **可观测性** | 本地日志文件 | **LLM Tracing (LangFuse/Arize)** | 建议接入 LLM 专用监控平台，追踪 Token 消耗、延迟和 Prompt 版本。 |

## 3. 已完成的优化与重构 (本次 Session)

针对最核心的 "LLM 交互" 问题，我们已经完成了底层服务的现代化改造：

### 3.1 `llm_service.py` 重构
- **移除**：移除了手动构建 HTTP 请求的 `requests` 调用。
- **新增**：引入了官方 `openai` Python SDK。
- **新增**：增加了 `call_llm_structured` 方法，支持传入 Pydantic 模型，利用 LLM 原生的结构化输出能力（Structured Outputs），这将彻底解决 YAML 解析失败的问题。
- **兼容性**：保留了 `call_llm` 接口和 `parse_yaml_response`，确保现有业务逻辑（Captain/Manager 等）不中断，但建议后续逐步迁移。

### 3.2 依赖升级
- 安装并升级了 `openai>=1.0.0`, `pydantic>=2.0.0`, `sqlalchemy>=2.0.0` 等核心库，确保项目运行在现代技术栈上。

## 4. 后续优化建议 (Roadmap)

### 短期 (1-2周)
1.  **迁移 Agent 逻辑**：将 `_captain`, `_manager` 等角色的 Prompt 逻辑重构，不再要求输出 YAML，而是直接定义 Pydantic Model（如 `TaskDefinition`, `ActionItem`），传入 `call_llm_structured`。
2.  **清理 Prompt**：简化 `app/prompts/default_prompts.py`，移除关于 "必须输出 YAML" 的长篇大论，让模型专注于业务逻辑。

### 中期 (1-2月)
1.  **MCP 标准化集成 (SOAR as MCP Server)**:
    - 鉴于开源项目 `soar-mcp` (https://github.com/flagify-com/soar-mcp) 已实现将 SOAR 剧本直接转换为 MCP Resources/Tools，DeepSOC 应全面转型为 **MCP Client**。
    - **弃用 Playbook Prompts**: 不再需要在 Prompt 中硬编码或 RAG 检索 Playbook 列表。
    - **动态工具发现**: Agent (如 Manager/Operator) 启动时连接 SOAR MCP Server，动态获取当前可用工具列表，直接通过 LLM Function Calling 调用，极大简化 Prompt 工程。
2.  **异步化改造**：将 Flask Controller 和 Agent Service 改为 `async/await` 模式，提高高并发下的吞吐量。

### 长期
1.  **多 MCP Server 协同**: 不仅连接 SOAR，还可以连接 CMDB, Threat Intelligence 等其他 MCP Server，实现真正的工具生态互联。

## 5. 总结
DeepSOC 的基础架构是稳固的。本次重构解决了最底层的 LLM 调用方式问题，为上层的智能化升级打下了基础。接下来的重点应放在 **结构化输出迁移** 和 **RAG 知识库构建** 上。
