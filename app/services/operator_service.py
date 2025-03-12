import time
import uuid
import json
from datetime import datetime
from flask import current_app
from sqlalchemy import func
from app.models import db, Event, Task, Action, Command, Message
from app.services.llm_service import call_llm, parse_yaml_response
from app.controllers.socket_controller import broadcast_message
from app.services.prompt_service import PromptService
from app.utils.message_utils import create_standard_message
import yaml
import logging
logger = logging.getLogger(__name__)

def get_pending_actions():
    """获取待处理的动作，按照event_id和round_id分组
    
    Returns:
        字典，键为(event_id, round_id)元组，值为该组的动作列表
    """
    # 查询所有pending状态的动作
    pending_actions = Action.query.filter_by(action_status='pending').order_by(Action.created_at.asc()).all()
    
    # 按照event_id和round_id分组
    grouped_actions = {}
    for action in pending_actions:
        key = (action.event_id, action.round_id)
        if key not in grouped_actions:
            grouped_actions[key] = []
        grouped_actions[key].append(action)
    
    return grouped_actions

def process_action_group(event_id, round_id, actions):
    """处理一组动作
    
    Args:
        event_id: 事件ID
        round_id: 轮次ID
        actions: 动作列表
    """
    logger.info(f"处理事件 {event_id} 轮次 {round_id} 的动作组，共 {len(actions)} 个动作")
    
    # 获取事件信息
    event = Event.query.filter_by(event_id=event_id).first()
    if not event:
        logger.error(f"事件 {event_id} 不存在")
        return
    
    actions_data = []
    for action in actions:
        # 获取关联的任务
        task = Task.query.filter_by(task_id=action.task_id).first()
        task_name = task.task_name if task else "未知任务"
        
        actions_data.append({
            'action_id': action.action_id,
            'action_name': action.action_name,
            'action_type': action.action_type,
            'task_id': action.task_id,
            'task_name': task_name
        })

    request_data = {
        'type': 'generate_commands_by_actions',
        'req_id': str(uuid.uuid4()),
        'res_id': str(uuid.uuid4()),
        'event_id': event_id,
        'event_round': round_id,
        'event_name': event.event_name,
        'event_message': event.message,
        'actions': actions_data
    }
    
    yaml_data = yaml.dump(request_data, allow_unicode=True, default_flow_style=False, indent=2)

    # 构建用户提示词
    user_prompt = f"""
```yaml
{yaml_data}
```

请根据以上动作要求，输出可以供`_executor`通过机器执行的`COMMAND`。
"""
    logger.info(user_prompt)
    logger.info("--------------------------------")
    
    # 调用大模型
    prompt_service = PromptService('_operator')
    system_prompt = prompt_service.get_system_prompt()

    logger.info(f"请求大模型：{event_id} - {round_id}")
    create_standard_message(
        event_id=event_id,
        message_from='system',
        round_id=round_id,
        message_type='llm_request',
        content_data="正在请求大模型，理解安全管理员的动作，并细化成命令，请耐心等待......"
    )
    response = call_llm(system_prompt, user_prompt)
    logger.info(response)
    logger.info("--------------------------------")

    # 解析响应
    parsed_response = parse_yaml_response(response)
    if not parsed_response:
        logger.error(f"解析响应失败: {response}")
        return
    
    # 创建消息记录
    create_standard_message(
        event_id=event_id,
        message_from='_operator',
        round_id=round_id,
        message_type='llm_response',
        content_data=parsed_response
    )
    
    # 处理响应，更新动作状态和任务状态
    process_operator_response(parsed_response, actions)

def process_operator_response(response, actions):
    """处理操作员响应，更新动作状态和任务状态
    
    Args:
        response: 解析后的响应对象
        actions: 动作列表
    """
    # 获取响应类型
    response_type = response.get('response_type')
    
    # 如果是动作执行结果
    if response_type == 'COMMAND':
        # 获取结果列表
        commands = response.get('commands', [])
        
        # 创建命令
        for command_data in commands:
            # 获取关联的动作
            action_id = command_data.get('action_id')
            action = next((a for a in actions if a.action_id == action_id), None)
            
            if not action:
                logger.error(f"动作 {action_id} 不存在")
                continue
            
            # 创建命令
            command = Command(
                command_id=str(uuid.uuid4()),
                command_type=command_data.get('command_type'),
                command_name=command_data.get('command_name'),
                command_assignee=command_data.get('command_assignee'),
                action_id=action_id,
                task_id=command_data.get('task_id'),
                round_id=response.get('round_id'),
                event_id=response.get('event_id'),
                command_entity=command_data.get('command_entity', {}),
                command_params=command_data.get('command_params', {}),
                command_status='pending'
            )
            db.session.add(command)
            
            # 更新动作状态为处理中
            action.action_status = 'processing'
            
        db.session.commit()
        logger.info(f"已创建 {len(commands)} 个命令")

def run_operator():
    """运行_operator服务"""
    logger.info("启动_operator服务...")
    
    # 导入Flask应用
    from main import app
    
    # 使用应用上下文
    with app.app_context():
        while True:
            try:
                # 获取待处理动作组
                grouped_actions = get_pending_actions()
                
                if grouped_actions:
                    logger.info(f"发现 {len(grouped_actions)} 组待处理动作")
                    
                    # 处理每组动作
                    for (event_id, round_id), actions in grouped_actions.items():
                        process_action_group(event_id, round_id, actions)
                else:
                    logger.info("没有待处理动作，等待中...")
                    time.sleep(5)
            except Exception as e:
                logger.error(f"处理动作时出错: {e}")
                time.sleep(5)