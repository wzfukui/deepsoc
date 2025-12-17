# DeepSOC 架构重构设计文档：基于 MCP 的多 Agent 协作模型

## 1. 核心理念

本次重构旨在引入 **MCP (Model Context Protocol)** 标准，以替代原有的硬编码工具调用方式，同时**坚持并深化** DeepSOC 的多角色分工体系。

我们认为，安全运营的本质是**分层决策与执行**：
*   **战略层**需要推理能力强的大模型，专注于大局；
*   **战术层**需要理解业务逻辑，进行任务拆解；
*   **执行层**需要精确的指令遵循能力，负责工具的具体调用与结果清洗。

MCP 协议将作为**底层能力**支撑这一体系，但不同角色对 MCP 的感知程度不同。

## 2. 角色职能与 MCP 感知矩阵

| 角色 | 英文名 | 职能定位 | 对 MCP 的感知程度 | 推荐模型类型 |
| :--- | :--- | :--- | :--- | :--- |
| **指挥官** | `_captain` | **战略决策 (Strategy)**<br>负责态势感知、定性分析、发布高层任务。 | **无 (None)**<br>不关心具体工具，只关心“需要调查IP”这一目标。 | **强推理模型**<br>(DeepSeek R1, GPT-4o, o1) |
| **安全经理** | `_manager` | **任务拆解 (Planning)**<br>将高层任务拆解为可执行步骤。 | **弱 (Weak)**<br>只知道有哪些工具可用（名称/描述），用于判断任务可行性，但不涉及参数。 | **均衡模型**<br>(Claude 3.5 Sonnet, GPT-4o) |
| **工程师** | `_operator` | **工具编排 (Orchestration)**<br>选择具体工具，生成调用参数。 | **强 (Strong)**<br>加载完整的 MCP Tool Schema，负责将自然语言任务转化为结构化的 Tool Calls。 | **指令遵循模型**<br>(Claude 3.5 Sonnet, GPT-4o) |
| **执行器** | `_executor` | **动作执行 (Execution)**<br>实际连接工具，清洗数据。 | **执行 (Runtime)**<br>负责 MCP Client 连接、调用、以及对海量返回结果的**摘要**。 | **长文本/高性价比模型**<br>(GPT-4o-mini, Qwen-Long) |

## 3. 协作流程详解 (Workflow)

假设事件：*检测到内部主机 192.168.1.5 存在异常外连行为。*

### Phase 1: 战略研判 (Captain)
*   **Input**: 安全事件详情。
*   **Thinking**: "这是一起潜在的 C2 通信事件，需要确认主机的进程状态和网络连接详情。"
*   **Output (Task)**:
    1.  调查 192.168.1.5 的网络连接情况。
    2.  检查该主机的可疑进程。

### Phase 2: 任务拆解 (Manager)
*   **Input**: Task "调查 192.168.1.5 的网络连接情况"。
*   **Context**: 系统中安装了 `Nmap Scanner`, `SSH Connector` 等 MCP Server。
*   **Thinking**: "要调查网络连接，可以使用 Nmap 扫描端口，或者用 SSH 登录查看 netstat。"
*   **Output (Action)**:
    1.  使用 Nmap 扫描 192.168.1.5 的开放端口 (Action Type: `scan`)。
    2.  (可选) 如果有凭证，SSH 登录查看连接 (Action Type: `inspect`)。

### Phase 3: 工具选择与参数生成 (Operator)
*   **Input**: Action "使用 Nmap 扫描 192.168.1.5"。
*   **Tool Registry**: 加载 MCP 工具定义，发现 `nmap-scanner` Server 下有 `nmap_quick_scan` 工具。
*   **Thinking**: "匹配到 `nmap_quick_scan` 工具，目标是 IP。"
*   **Output (Command)**:
    *   Tool: `nmap-scanner__nmap_quick_scan`
    *   Arguments: `{"target": "192.168.1.5"}`

### Phase 4: 执行与摘要 (Executor)
*   **Input**: Command (Tool Call)。
*   **Execution**: 通过 MCP Client 调用远程 Nmap Server。
*   **Raw Result**: 返回 200 行 Nmap 扫描日志。
*   **Processing**: 调用轻量级 LLM 进行摘要。
*   **Output (Execution Result)**: "扫描完成。发现开放端口: 80 (HTTP), 443 (HTTPS), 22 (SSH)。无高危漏洞端口。"
*   **Feedback**: 结果逐级回传，最终存入 Event Context 供 Captain 下一轮参考。

## 4. 数据库设计变更回顾

*   `MCPServer`: 存储 Server 配置 (url, token, etc.)。
*   `MCPTool`: 存储同步下来的 Schema (name, description, input_schema)。
*   `Task`, `Action`, `Command`, `Execution`: 现有的任务流转表结构基本保持不变，只需在 `Command` 表中增加对 MCP Tool 的字段支持（或复用现有字段）。

## 5. 模块改造计划

### 5.1 Captain Service
*   **回滚**: 去除直接调用 `MCPManager` 的逻辑。
*   **优化**: 优化 System Prompt，使其专注于生成清晰、非技术性的业务任务。

### 5.2 Manager Service
*   **增强**: 在 Prompt 中注入 "Available Tools List" (仅 Name/Description)，让 Manager 知道能力边界。
*   **输出**: 继续输出 `Action` 列表。

### 5.3 Operator Service
*   **核心**: 实现 Tool Selection 逻辑。
*   **Prompt**: "你是一个工程师，你的任务是完成这个 Action。这是当前可用的工具详细定义 (JSON Schema)... 请生成 Tool Call。"

### 5.4 Executor Service
*   **核心**: 集成 `MCPManager.execute_tool`。
*   **增强**: 增加 "Result Summarization" 步骤，避免把几万字的原始日志直接扔进数据库，撑爆上层 Agent 的 Context Window。

---
*文档版本: v1.0 | 日期: 2025-12-17*
