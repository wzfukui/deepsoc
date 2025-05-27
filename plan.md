# DeepSOC 消息机制改造计划 (技术版)

**计划ID:** 20240728-RMQ-MSG-001
**创建日期:** 2024-07-28
**负责人:** (待分配)
**状态:** 规划中

## 1. 目标

重构 DeepSOC 系统的后端到前端消息通知机制，引入 RabbitMQ 作为核心消息队列，以解决当前多 Agent 进程无法直接、可靠地向前端发送通知的问题，并建立一个通用的、可扩展的底层消息交互基础。

## 2. 背景与问题

当前系统存在以下问题：
- 仅主 Web 进程能发送 WebSocket 消息。
- 其他独立运行的 Agent 进程（如指挥官、经理等）无法直接通过 WebSocket 通知前端。
- 缺乏统一的、可靠的消息中间件，导致消息传递受限于主进程的可用性。

## 3. 整体方案

采用 RabbitMQ 作为消息队列，实现 Agent 进程与主 Web 进程的解耦。

1.  **消息生产者 (Producers)**: 各 Agent 进程（`captain_service`, `manager_service` 等）在需要通知前端时，将格式化的消息发布到 RabbitMQ 的指定交换机 (Exchange) 和路由键 (Routing Key)。
2.  **消息队列 (RabbitMQ)**: 配置一个或多个交换机和队列，用于暂存和路由 Agent 发送的消息。
3.  **消息消费者 (Consumer)**: 主 Web 进程 (`main.py`) 中启动一个或多个 RabbitMQ 消费者。这些消费者订阅相关队列，接收消息后进行处理：
    *   将消息内容持久化到数据库 (`Message` 表)。
    *   通过已建立的 `Flask-SocketIO` 连接，将消息实时推送给对应的前端客户端 (基于 `event_id` 等进行房间路由)。

## 4. 技术选型

- **消息队列**: RabbitMQ
- **Python RabbitMQ 客户端库**: Pika

## 5. 详细实施步骤

### 阶段一：环境准备与基础设置 (预计1-2天)

1.  **安装与配置 RabbitMQ 服务**:
    *   [ ] 在开发和生产环境部署 RabbitMQ 服务。
    *   [ ] 记录 RabbitMQ 连接信息 (host, port, user, password, vhost)。
2.  **项目依赖更新**:
    *   [ ] 在 `requirements.txt` 中添加 `pika` 库。
    *   [ ] 运行 `pip install -r requirements.txt` 安装。
3.  **环境变量配置**:
    *   [ ] 在 `.env` 和 `sample.env` 文件中添加 RabbitMQ 连接参数 (e.g., `RABBITMQ_HOST`, `RABBITMQ_PORT`, `RABBITMQ_USER`, `RABBITMQ_PASSWORD`, `RABBITMQ_VHOST`)。
4.  **RabbitMQ 核心组件定义**:
    *   [ ] **交换机 (Exchange)**: 定义一个名为 `deepsoc_notifications_exchange` 的 `topic` 类型交换机。 Topic 类型允许灵活的路由。
    *   [ ] **队列 (Queue)**: 定义一个名为 `frontend_notifications_queue` 的持久化队列，用于接收所有发往前端的通知。
    *   [ ] **绑定 (Binding)**: 将 `frontend_notifications_queue` 绑定到 `deepsoc_notifications_exchange`，使用路由键 `#` (井号) 来接收所有该交换机上的消息，或者更细致的路由键如 `notifications.frontend.#`。

### 阶段二：Agent 进程改造 - 消息发布 (预计2-3天)

针对每个相关的 Agent 服务 (e.g., `app/services/captain_service.py`, `app/services/manager_service.py`, etc.):
1.  **RabbitMQ 连接工具**:
    *   [ ] 创建一个通用的 RabbitMQ 连接和发布工具类/函数 (e.g., in `app/utils/mq_utils.py`)，处理连接建立、信道获取、消息发布、连接关闭等。
    *   [ ] 该工具应能从环境变量中读取 RabbitMQ 配置。
2.  **消息构造与发布**:
    *   [ ] 在 Agent 服务中，当需要发送通知给前端时（例如任务分配、状态更新、专家结论生成等），构造符合 `app.models.models.Message` 结构的消息字典。
        *   关键字段: `event_id`, `message_from` (e.g., 'captain'), `message_content`, `message_type`。
    *   [ ] 将消息字典序列化为 JSON 字符串。
    *   [ ] 使用 RabbitMQ 发布工具，将 JSON 消息发布到 `deepsoc_notifications_exchange`，并指定一个合适的路由键 (e.g., `notifications.frontend.<event_id>.<message_type>`).
    *   [ ] 考虑消息发送的可靠性，如使用 publisher confirms。
3.  **移除旧的消息发送逻辑**:
    *   [ ] 移除 Agent 中原有的、尝试直接写数据库 `Message` 表（如果目的是为了通知前端）或间接调用 SocketIO 的逻辑。

### 阶段三：主 Web 进程改造 - 消息消费与推送 (预计2-3天)

在主 Web 应用 (`main.py` 或相关模块如 `app/services/notification_service.py`):
1.  **RabbitMQ 消费者实现**:
    *   [ ] 实现一个 RabbitMQ 消费者类或函数。
    *   [ ] 该消费者将连接到 RabbitMQ，声明/确保交换机和队列存在，并将队列绑定到交换机。
    *   [ ] 订阅 `frontend_notifications_queue`。
2.  **消息处理回调**:
    *   [ ] 在消费者收到消息时的回调函数中：
        *   [ ] 反序列化 JSON 消息。
        *   [ ] **数据持久化**: 在 Flask 应用上下文中，创建 `Message` ORM 对象并保存到数据库。
        *   [ ] **WebSocket 推送**: 获取 `socketio` 实例，使用 `socketio.emit('new_message', message_dict, room=event_id)` 将消息推送到前端。
        *   [ ] **消息确认 (Acknowledgement)**: 成功处理消息后，向 RabbitMQ 发送 `ack`，确保消息从队列中移除。如果处理失败，考虑 `nack` 并决定是否重入队列。
3.  **消费者启动与管理**:
    *   [ ] 在 `main.py` 启动 Flask 应用后，在一个独立的后台线程中启动 RabbitMQ 消费者。
    *   [ ] 考虑消费者的健壮性，如连接断开后的自动重连机制。
4.  **SocketIO 适配**:
    *   [ ] 确保 `app/controllers/socket_controller.py` 中的 `broadcast_message` (如果还被其他地方直接调用) 与新的消息流协调，或者其功能被 MQ 消费者完全取代。

### 阶段四：测试与联调 (预计2-3天)

1.  **单元测试**:
    *   [ ] 针对 MQ 发布工具、消息构造逻辑、MQ 消费者回调逻辑编写单元测试。
2.  **集成测试**:
    *   [ ] 模拟 Agent 发送消息，验证消息能否通过 RabbitMQ 正确到达消费者，并被存入数据库、推送到前端。
    *   [ ] 测试不同 Agent 角色的消息发送。
    *   [ ] 测试前端 WebSocket 接收和展示。
3.  **异常场景测试**:
    *   [ ] RabbitMQ 服务不可用时的 Agent 行为和消费者行为。
    *   [ ] 消息处理失败时的 `nack` 和重试（如果实现）。
    *   [ ] WebSocket 连接断开时的消息处理。

### 阶段五：文档与清理 (预计1天)

1.  **更新文档**:
    *   [ ] 更新 `DeepSOC架构文档.md`，详细描述新的基于 RabbitMQ 的消息机制，包括架构图。
    *   [ ] 更新开发者文档，说明如何使用新的消息发布机制。
2.  **代码审查与优化**:
    *   [ ] 对所有修改进行代码审查。
    *   [ ] 清理不再使用的旧代码。
3.  **更新 `changelog.md`**:
    *   [ ] 详细记录本次消息机制的重大变更。

## 6. 风险与应对

- **RabbitMQ 运维复杂性**: 需要有人员熟悉 RabbitMQ 的部署和管理。
    *   *应对*: 初期使用云托管的 RabbitMQ 服务 (如 CloudAMQP) 或 Docker 部署简化管理。
- **消息处理失败**: 消费者处理消息时可能发生异常。
    *   *应对*: 实现完善的错误处理、日志记录，并根据业务需求决定是否使用死信队列 (DLX) 或重试机制。
- **Pika 库的异步使用**: Pika 的某些用法（特别是与 Flask/SocketIO 的线程模型集成）需要注意，避免阻塞。
    *   *应对*: 仔细查阅 Pika 文档，确保在独立线程中正确使用阻塞式消费者，或采用其异步适配器。

## 7. 预期成果

- Agent 进程能够可靠、异步地将通知消息发送给前端。
- 系统消息传递机制更加健壮、解耦和可扩展。
- 前端用户能够及时收到来自各个虚拟角色的操作和事件更新。

## Phase 5: Resolve Frontend Message Duplication and Optimize Message Loading

**Goal**: Prevent duplicate messages on the frontend and optimize message loading by using unique database IDs.

**Tasks**:

1.  **[x] Backend: Ensure Database ID in MQ Messages**:
    *   **File**: `app/utils/message_utils.py`
        *   **Action**: Modify `create_standard_message` to ensure the `message.id` (after being saved to the database) is included in the dictionary that will be sent to RabbitMQ. The function should ideally return the message object or at least the dictionary containing its `db_id`. (Verified: Existing code meets requirements)
    *   **Files**: `app/services/captain_service.py`, `app/services/manager_service.py`, `app/services/operator_service.py`, `app/services/executor_service.py`, `app/services/expert_service.py`
        *   **Action**: Verify and adjust: when these services prepare the message dictionary to be published by `RabbitMQPublisher`, ensure a field like `db_id` (obtained from the result of `create_standard_message` or the message object itself) is included. The message structure sent to MQ should be consistent, e.g., `{'db_id': message_db_id, 'event_id': ..., 'content': ..., 'source': ..., 'type': ..., 'timestamp': ...}`. (Verified: Existing code using `Message.to_dict()` which includes `id` meets requirements)

2.  **[x] Backend: Pass Database ID via WebSocket**:
    *   **File**: `main.py`
        *   **Action**: Modify the `handle_mq_message_to_socketio` callback function. When a message is received from RabbitMQ, ensure the `db_id` (extracted from the MQ message body) is included in the data payload emitted via `socketio.emit('new_message', ...)`. (Verified: Existing code sends the full `message_data` dict which includes `id`)

3.  **[x] Backend: Enhance Message Fetch API for Incremental Loading**:
    *   **Identify**: Locate the API endpoint and controller function responsible for fetching messages for a given event (e.g., `GET /api/events/<event_id>/messages`).
    *   **File**: `app/controllers/event_controller.py`
        *   **Action**: Modify the API endpoint to accept an optional query parameter, e.g., `last_message_db_id` (integer). (Completed: Parameter changed to `last_message_db_id`)
        *   **Action**: Update the corresponding controller function to filter messages: if `last_message_db_id` is provided, query the database for messages belonging to the specified `event_id` where `message.id > last_message_db_id`. Messages should be ordered by `message.id` (ascending). If `last_message_db_id` is not provided, return all messages for the event (or a recent, paginated set, ensuring ascending order of IDs for consistency). (Completed: Logic updated and sorting by `Message.id.asc()` implemented)

4.  **Frontend: Implement De-duplication and Incremental Loading Logic (Guidance for Frontend Developer)**:
    *   **Data Structure**: Maintain a client-side Set or sorted list of `db_id`s for messages already displayed in the current event room.
    *   **WebSocket Message Handling (`new_message` event)**:
        *   Extract `db_id` from the incoming message payload.
        *   If `db_id` is already in the client-side Set/list, ignore the message.
        *   Otherwise, render the message and add `db_id` to the Set/list.
    *   **API Message Fetching (Polling/Initial Load)**:
        *   Before making an API call to fetch messages:
            *   Find the largest `db_id` from the currently displayed messages.
            *   If a `db_id` is found, include it as the `last_message_db_id` query parameter in the API request.
        *   When new messages are received from the API, iterate through them. For each message, check its `db_id` against the client-side Set/list. If not already present, render it and add the `db_id`.
    *   **Initial Load/Page Refresh**:
        *   When an event room is first loaded or refreshed, make the API call without the `last_message_db_id` parameter to get an initial set of messages. Render these and populate the client-side `db_id` Set/list.

5.  **Documentation**:
    *   [x] Update `changelog.md`: Add entries detailing the backend changes for message ID propagation and API enhancement. Also, briefly note the frontend de-duplication strategy. (Completed)
    *   [ ] Update `DeepSOC架构文档.md`: If necessary, refine the section on message flow to include the role of `db_id` in ensuring message consistency and optimizing frontend updates. (Pending, as needed)

---
**注:** 此计划为初步规划，具体任务和时间安排可能根据实际开发进展进行调整。 