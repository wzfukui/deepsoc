// 测试消息解析逻辑的独立脚本
// 使用方法：node tools/test_message_parsing.js

// 模拟extractMessageData函数
function extractMessageData(content) {
    if (!content) {
        return content;
    }
    
    let result = content;
    
    // First level: handle string or object
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
    
    // Second level: check if result.text is a JSON string and parse it
    if (result && typeof result === 'object' && result.text && typeof result.text === 'string') {
        try {
            const parsedText = JSON.parse(result.text);
            if (parsedText && typeof parsedText === 'object') {
                return parsedText;
            }
        } catch (e) {
            // If text is not valid JSON, return result as-is
            return result;
        }
    }
    
    return result;
}

// 测试数据：来自实际API响应
const testMessage = {
    "chat_session_id": null,
    "created_at": "2025-12-18T03:32:07",
    "event_id": "abfbc176-0397-4c05-8e76-26dfaa11c0c3",
    "event_summary_version": null,
    "id": 3,
    "message_category": "agent",
    "message_content": {
        "data": {
            "text": '{\n  "type": "llm_response",\n  "from": "_captain",\n  "to": "_manager",\n  "event_id": "abfbc176-0397-4c05-8e76-26dfaa11c0c3",\n  "round_id": 1,\n  "event_name": "外部IP对邮件网关服务器进行暴力破解攻击",\n  "response_type": "TASK",\n  "response_text": "当前事件为中危安全事件，攻击源为外部IP 66.240.205.34，目标为邮件网关服务器（192.168.22.251），存在暴力破解行为。",\n  "tasks": [\n    {\n      "task_assignee": "_analyst",\n      "task_type": "query",\n      "task_name": "查询外部IP地址66.240.205.34的威胁情报信息"\n    },\n    {\n      "task_assignee": "_analyst",\n      "task_type": "query",\n      "task_name": "查询内网IP 192.168.22.251最近24小时内的SSH和SMTP服务登录日志"\n    }\n  ]\n}'
        },
        "timestamp": "2025-12-18T11:32:07.448098"
    },
    "message_from": "_captain",
    "message_id": "c167bb9a-a8d6-4800-bcbb-76d48bb6d088",
    "message_type": "llm_response",
    "round_id": 1,
    "sender_type": null,
    "updated_at": "2025-12-18T03:32:07",
    "user_id": null
};

console.log('=== 测试消息解析 ===\n');

console.log('1. 原始 message_content:');
console.log(JSON.stringify(testMessage.message_content, null, 2));

console.log('\n2. 调用 extractMessageData 后:');
const extractedData = extractMessageData(testMessage.message_content);
console.log(JSON.stringify(extractedData, null, 2));

console.log('\n3. 验证解析结果:');
console.log('- response_type:', extractedData.response_type);
console.log('- response_text:', extractedData.response_text?.substring(0, 50) + '...');
console.log('- tasks数组长度:', extractedData.tasks?.length);

if (extractedData.tasks && extractedData.tasks.length > 0) {
    console.log('\n4. 任务列表:');
    extractedData.tasks.forEach((task, index) => {
        console.log(`  任务${index + 1}:`, task.task_name);
        console.log(`    - 分配给: ${task.task_assignee}`);
        console.log(`    - 类型: ${task.task_type}`);
    });
    console.log('\n✅ 消息解析成功！任务列表已正确提取。');
} else {
    console.log('\n❌ 消息解析失败！无法提取任务列表。');
}

console.log('\n5. 测试不同类型的消息:');

// 测试简单文本消息
const simpleMessage = {
    type: 'text',
    text: 'Hello World'
};
console.log('简单消息:', extractMessageData(simpleMessage));

// 测试嵌套数据消息
const nestedMessage = {
    data: {
        response_text: 'Nested response'
    }
};
console.log('嵌套消息:', extractMessageData(nestedMessage));

console.log('\n=== 测试完成 ===');
