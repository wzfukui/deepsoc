# DeepSOC 前后端通讯数据结构与交互审查报告

**日期**: 2025-12-17
**审查对象**: 数据模型 (Models), 消息流 (MQ/SocketIO), 前端处理 (JS)

## 1. 现状概述

DeepSOC 目前采用 **混合式架构** 进行前后端通讯：
-   **RESTful API**: 用于获取初始状态（事件详情、历史消息、统计数据）。
-   **WebSocket (Socket.io)**: 用于实时推送增量更新（新消息、状态变更）。
-   **RabbitMQ**: 作为后端 Agent 与 Web 服务之间的异步消息总线。

数据载体主要依赖数据库中的 `Message` 表，其核心是一个灵活的 JSON 字段 `message_content`。

## 2. 数据结构分析

### 2.1 后端模型 (`Message`)
-   **设计**: 采用了 "信封模式" (Envelope Pattern)。
    ```python
    class Message(db.Model):
        message_id = ...
        event_id = ...
        message_type = ... # e.g., 'llm_response', 'command_result'
        message_content = JSON # 实际负载
    ```
-   **评价**: 
    -   ✅ **灵活性高**: `JSON` 类型允许存储任意结构的 Payload，适应 LLM 多变的输出。
    -   ✅ **查询优化**: `event_id` 和 `round_id` 有独立字段，方便索引和过滤。
    -   ⚠️ **类型弱约束**: `message_type` 是字符串，缺乏严格的 Schema 验证，容易导致前后端对某些字段的定义不一致。

### 2.2 消息流转格式
-   **Agent -> MQ**: Agent 调用 `create_standard_message` 生成消息，结构如下：
    ```json
    {
      "timestamp": "ISO8601...",
      "data": { ...业务数据... }
    }
    ```
-   **MQ -> WebSocket -> Frontend**: 消费者直接透传数据库对象的 `to_dict()` 结果。
-   **问题**: 
    -   🔴 **JSON String 嵌套**: 代码中存在迹象（如 `warroom.js` 中的 `extractMessageData`），表明某些 `message_content` 字段在传输时可能被序列化成了 JSON 字符串，导致前端需要进行 `JSON.parse` 的二次解析。这是一种反模式，增加了前端的复杂性和出错率。

## 3. 前端处理逻辑审查 (`warroom.js`)

这是目前系统中**技术债最重**的部分。

-   **God Script 问题**: `warroom.js` 单文件超过 2400 行，承担了 WebSocket 连接、重连逻辑、DOM 操作、业务逻辑路由、Markdown 渲染等所有职责。
-   **硬编码的 `if-else`**: `addMessage` 函数包含巨大的 `if-else` 链来处理不同类型的 `message_type`。每新增一种消息类型，都需要修改这个核心函数，违反了 "开闭原则" (Open-Closed Principle)。
-   **状态管理缺失**: 前端主要依赖 DOM 作为状态的 "从属存储" (Source of Truth)，缺乏统一的状态管理（如 Store），这在处理复杂的 "Bento Grid" 或 "Timeline" 视图时会非常吃力。

## 4. 优化建议

### 4.1 数据结构与协议优化
1.  **消除嵌套序列化**: 确保后端 API 和 WebSocket 推送的 `message_content` 永远是 **JSON Object**，而不是 **JSON String**。在存入数据库前或取出时进行统一处理。
2.  **引入 Schema 验证**: 虽然 Python 是动态语言，但建议使用 `Pydantic` 定义各类消息（如 `TaskMessage`, `ActionMessage`）的结构，作为前后端交互的 "契约"。
3.  **标准化 Message Type**: 将分散的字符串字面量（如 `'llm_response'`, `'command_result'`）统一为枚举类或常量定义，避免拼写错误。

### 4.2 前端重构 (高优先级)
为了支撑即将到来的 UI/UX 升级（Clean Dark / Bento Grid），前端必须重构：

1.  **组件化**: 废弃 jQuery 风格的 DOM 操作，引入 **Vue.js 3** 或 **React**。
    -   `MessageList` 组件
    -   `EventStatus` 组件
    -   `ExecutionPanel` 组件
2.  **状态管理**: 使用 Pinia (Vue) 或 Zustand/Redux (React) 管理 WebSocket 连接状态和消息列表。
3.  **TypeScript**: 引入 TypeScript 定义消息接口，与后端的 Pydantic 模型对应，实现端到端的类型安全。

### 4.3 交互体验优化
1.  **乐观 UI (Optimistic UI)**: 用户发送消息时，前端先立即上屏（`pending` 状态），待服务器确认后再更新状态，消除网络延迟感。（目前已有部分实现，需通过框架固化）。
2.  **增量更新**: 目前 `get_event_hierarchy` 每次返回全量树结构。对于大型事件，应改为只推送变更的节点（Delta Update）。

## 5. 结论
当前的数据结构足以支撑现有功能，但**前端实现方式严重落后于行业标准**。如果不进行组件化重构，任何 UI 风格的升级都将是 "在沙滩上建高楼"。

**建议路线**:
1.  后端：清理 JSON 序列化逻辑。
2.  前端：启动 Vue.js/React 重构项目，逐步替换 `warroom.js`。
