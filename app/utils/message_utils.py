import uuid
from datetime import datetime
from app.models import db, Message
from app.controllers.socket_controller import broadcast_message

def create_standard_message(event_id, message_from, round_id, message_type, content_data, additional_fields=None):
    """创建标准格式的消息
    
    Args:
        event_id: 事件ID
        message_from: 消息来源 (_captain, _manager, _operator, _executor, _expert)
        round_id: 轮次ID
        message_type: 消息类型 (llm_response, execution_summary, event_summary, command_result)
        content_data: 消息主体内容
        additional_fields: 额外字段
    
    Returns:
        创建的消息对象
    """
    # 构造标准消息内容
    message_content = {
        "type": message_type,
        "timestamp": datetime.now().isoformat(),
        "data": content_data
    }
    
    # 添加额外字段
    if additional_fields:
        message_content.update(additional_fields)
    
    # 创建消息记录
    message = Message(
        message_id=str(uuid.uuid4()),
        event_id=event_id,
        message_from=message_from,
        round_id=round_id,
        message_content=message_content,
        message_type=message_type
    )
    db.session.add(message)
    db.session.commit()
    
    # 广播消息
    broadcast_message(message)
    
    return message 