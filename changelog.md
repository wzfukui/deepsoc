# Changelog

## 2025-12-17
### 重构：架构升级与 MCP 集成
- **移除 SOAR 集成**：删除了原有的 SOAR 客户端、Playbook 服务及相关页面，转而全面使用 MCP 协议。
- **引入 MCP (Model Context Protocol)**：
  - 新增 `MCPServer` 和 `MCPTool` 数据库模型。
  - 新增 `app/mcp/` 模块，包含 MCP Client Manager 和工具发现逻辑。
  - 新增 MCP Server 管理后端 API (`/api/mcp/servers`)。
  - 新增 MCP Server 管理前端页面 (`/settings/mcp-tools`)，支持添加、编辑、同步和删除 MCP Server。
- **Agent 协作重构**：
  - 彻底重写 `app/services/captain_service.py`，Captain 现在直接使用 LLM Tool Calling 能力与 MCP 工具交互，无需通过 YAML 解析和 Task 分发。
  - 升级 `app/services/llm_service.py`，增加对 `tools` 参数和 `tool_calls` 响应的支持。
  - 停用 `_manager`, `_operator`, `_executor` 等中间 Agent 角色，简化系统架构。
