# Changelog

## 2025-12-17 (Update 3)
### Bug Fixes & UI Polish
- **UI 对比度修复 (Dark Mode Polish)**:
  - 修复了 `admin_dark.css` 和 `login.html` 在深色模式下的文字对比度问题，确保输入框、按钮和 Modal 弹窗内容清晰可见。
  - 为 Modal 弹窗强制应用深色背景和高对比度文字样式，解决 MCP 添加/编辑窗口文字不可见的问题。
- **Login Loop 修复**:
  - 修复了 `index.js` 中的登录重定向循环 (`auto-redirect loop`) 问题。增加了异步鉴权等待逻辑，防止在鉴权未完成时错误判断为未登录状态。
- **MCP Sync 修复**:
  - 修复了 MCP Server URL 包含 Query Parameters (如 Token) 时，同步工具失败的问题。

## 2025-12-17 (Update 2)
### UI/UX 优化：Clean Corporate Dark Mode (Admin Interface)
- **新建管理后台主题** (`admin_dark.css`)：
  - 实现类似 Linear/Vercel 的 Clean Corporate Dark Mode 风格。
  - 定义全新的深色调色板、卡片样式、状态指示器和高对比度字体。
- **重构管理仪表盘** (`admin_dashboard.html`)：
  - 更新布局为 Dashboard 风格，包含 Stats Cards, Quick Actions 面板和 Recent Alerts 列表。
  - 应用新的 CSS 主题。
- **登录页面优化** (`login.html`)：
  - 适配深色模式，优化卡片样式和品牌展示。
- **全站管理页面适配**：
  - 更新所有管理子页面（LLM设置、MCP工具、Prompt管理、用户管理、安全背景）以使用新主题。
  - 引入 `Inter` 字体以提升可读性。

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
