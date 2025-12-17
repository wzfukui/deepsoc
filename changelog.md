# Changelog

## 2025-12-17
### UI/UX 重构：Bento Grid 首页与独立管理后台
- **首页改版 (Bento Grid)**：
  - 重构首页 (`index.html`) 为 Bento Grid 布局，左侧展示事件创建面板，右侧展示实时事件列表。
  - 优化视觉体验，采用现代化卡片设计和响应式布局。
  - 根据用户登录状态动态显示/隐藏功能模块。
- **独立管理后台 (Admin Dashboard)**：
  - 创建独立的管理后台入口 `/admin`。
  - 实现侧边栏导航 (`admin_sidebar.html`)，整合所有系统配置功能。
  - 迁移以下功能至管理后台，并适配 Dark Theme (深色模式) 和新的布局结构：
    - **模型设置** (`/settings/llm`)：配置 Reasoning 和 Summary 模型参数。
    - **MCP 工具管理** (`/settings/mcp-tools`)：管理 MCP Server 和工具。
    - **提示词管理** (`/settings/prompts`)：管理各 Agent 角色的 Prompt。
    - **安全背景** (`/settings/background-security`)：编辑安全背景知识库。
    - **用户管理** (`/user-management`)：用户增删改查。
- **样式系统升级**：
  - 更新 `style.css`，引入 Bento Grid 系统、Admin Sidebar 样式及 Dark Mode 变量。
  - 统一全站字体和基础组件样式。

### 架构升级与 MCP 集成 (Earlier today)
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
