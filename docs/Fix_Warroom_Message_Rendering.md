# 作战室消息渲染修复文档

## 修复日期
2025-12-18

## 问题描述

### 1. 指挥官消息和任务不显示
前端从API拉取的消息数据无法正确渲染，特别是`_captain`的LLM响应消息中的任务列表。

**根本原因**：
- API返回的`message_content`结构为：
  ```json
  {
    "data": {
      "text": "{JSON字符串}"
    },
    "timestamp": "..."
  }
  ```
- 原有的`extractMessageData`函数只解析了第一层（`content.data`），没有继续解析`data.text`中的JSON字符串
- 导致`response_type`、`response_text`和`tasks`等字段无法被正确提取

### 2. 消息对齐混乱
- 系统消息、Agent消息、用户消息的对齐不统一
- 缺少明确的左/右对齐CSS类

## 修复内容

### 1. 修复消息数据解析（`warroom.js`）

**文件位置**：`/workspace/app/static/js/warroom.js`

**修改函数**：`extractMessageData(content)`

**修复逻辑**：
```javascript
function extractMessageData(content) {
    if (!content) {
        return content;
    }
    
    let result = content;
    
    // 第一层：处理字符串或对象
    if (typeof content === 'string') {
        try {
            const parsed = JSON.parse(content);
            if (parsed && typeof parsed === 'object') {
                result = (parsed.data !== undefined) ? parsed.data : parsed;
            }
        } catch (e) {
            return content;
        }
    } else if (typeof content === 'object') {
        result = (content.data !== undefined) ? content.data : content;
    }
    
    // 第二层：检查result.text是否为JSON字符串，如果是则解析
    if (result && typeof result === 'object' && result.text && typeof result.text === 'string') {
        try {
            const parsedText = JSON.parse(result.text);
            if (parsedText && typeof parsedText === 'object') {
                return parsedText;
            }
        } catch (e) {
            // 如果text不是有效JSON，返回result本身
            return result;
        }
    }
    
    return result;
}
```

**关键改进**：
- 添加了第二层解析逻辑
- 检查`result.text`是否为JSON字符串
- 如果是，则再次解析并返回解析后的对象
- 这样就能正确提取`response_type`、`response_text`、`tasks`等字段

### 2. 修复消息对齐（`warroom.js` + `warroom.css`）

#### JavaScript修改（`warroom.js`）

**addMessage函数中的class分配逻辑**：
```javascript
let baseClass = 'message';

// 确定基于角色的样式
if (roleClasses[message.message_from]) {
    baseClass += ' ' + roleClasses[message.message_from];
}

// 确定基于消息类型的对齐
if (message.message_from === 'system') {
    // 系统消息：居中对齐（由CSS处理）
} else if (message.message_from === 'user' || 
           (message.message_category === 'engineer_chat' && message.sender_type === 'user')) {
    // 用户消息：右对齐
    baseClass += ' message-user';
} else if (message.message_category === 'engineer_chat' && message.sender_type === 'ai') {
    // AI助手消息：左对齐，专家样式
    baseClass += ' message-expert message-agent';
} else {
    // 所有其他消息（agent等）：左对齐
    baseClass += ' message-agent';
}
```

#### CSS修改（`warroom.css`）

**添加的样式**：
```css
/* Agent Messages - Left Aligned (Default for all agents) */
.message-agent {
    align-self: flex-start;
}
```

**对齐规则总结**：
- **Agent消息**（`_captain`, `_manager`, `_operator`, `_executor`, `_expert`）：左对齐
- **用户消息**：右对齐
- **系统消息**：居中对齐
- **AI助手消息**：左对齐（使用expert样式）

### 3. 添加调试日志

**位置**：`warroom.js` 第970行

```javascript
else if (message.message_type === 'llm_response' || (message.message_type && message.message_type.includes('_llm_response'))) {
    console.log('[消息渲染] LLM Response数据:', data);
    // ...
}
```

**目的**：方便调试和追踪数据解析是否正确

## 测试验证

### 测试脚本
创建了独立的测试脚本：`/workspace/tools/test_message_parsing.js`

**运行方法**：
```bash
node tools/test_message_parsing.js
```

**测试结果**：✅ 所有测试通过

### 测试覆盖
1. ✅ 嵌套JSON字符串解析
2. ✅ `response_type`字段提取
3. ✅ `response_text`字段提取
4. ✅ `tasks`数组提取
5. ✅ 简单消息解析
6. ✅ 嵌套数据消息解析

## 使用说明

### 前端测试
1. 刷新作战室页面
2. 创建新事件或查看现有事件
3. 观察指挥官的消息和任务列表是否正确显示
4. 检查消息对齐是否正确：
   - Agent消息在左侧
   - 用户消息在右侧
   - 系统通知居中

### 浏览器控制台
查看消息渲染日志：
```
[消息渲染] LLM Response数据: {response_type: "TASK", response_text: "...", tasks: [...]}
```

## 影响范围

### 修改文件
1. `/workspace/app/static/js/warroom.js`
   - `extractMessageData()` 函数
   - `addMessage()` 函数中的class分配逻辑
   - LLM Response渲染部分（添加日志）

2. `/workspace/app/static/css/warroom.css`
   - 添加`.message-agent`样式

3. `/workspace/tools/test_message_parsing.js`（新建）
   - 消息解析测试脚本

### 向后兼容性
✅ 完全向后兼容

- 修复后的`extractMessageData`仍然支持旧的消息格式
- 如果`data.text`不是JSON字符串，会正常返回
- CSS修改只是添加新样式，不影响现有样式

## 相关Issue
- 指挥官消息不显示
- 任务列表无法渲染
- 消息对齐混乱

## 后续建议

### 1. 代码优化
虽然当前修复已经解决了核心问题，但`warroom.js`文件有2400+行，可以考虑：
- 拆分为多个模块（消息渲染、WebSocket管理、事件处理等）
- 使用ES6模块化
- 提取公共函数到utils文件

### 2. 类型安全
考虑使用TypeScript重写，提供更好的类型检查和IDE支持

### 3. 性能优化
- 消息渲染可以使用虚拟滚动
- 大量消息时考虑分页加载
- 优化DOM操作

### 4. 单元测试
为核心函数添加Jest单元测试：
- `extractMessageData`
- `addMessage`
- `formatDateTime`等辅助函数

## 总结

本次修复解决了作战室消息渲染的核心问题：

1. ✅ 修复了嵌套JSON字符串的解析逻辑
2. ✅ 修复了消息对齐问题
3. ✅ 添加了调试日志便于追踪
4. ✅ 创建了测试脚本验证修复
5. ✅ 保持了向后兼容性

现在指挥官的LLM响应消息和任务列表应该能够正确显示，消息对齐也更加统一和美观。
