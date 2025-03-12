import time
import uuid
import json
from datetime import datetime
from flask import current_app
from sqlalchemy import func
from app.models import db, Event, Task, Action, Message
from app.services.llm_service import call_llm, parse_yaml_response
from app.controllers.socket_controller import broadcast_message
from app.services.prompt_service import PromptService
from app.utils.message_utils import create_standard_message
import yaml
import logging
logger = logging.getLogger(__name__)


def get_pending_tasks():
    """获取待处理的任务，按照event_id和round_id分组
    
    Returns:
        字典，键为(event_id, round_id)元组，值为该组的任务列表
    """
    # 查询所有pending状态的任务
    pending_tasks = Task.query.filter_by(task_status='pending').order_by(Task.created_at.asc()).all()
    
    # 按照event_id和round_id分组
    grouped_tasks = {}
    for task in pending_tasks:
        key = (task.event_id, task.round_id)
        if key not in grouped_tasks:
            grouped_tasks[key] = []
        grouped_tasks[key].append(task)
    
    return grouped_tasks

def process_task_group(event_id, round_id, tasks):
    """处理一组任务
    
    Args:
        event_id: 事件ID
        round_id: 轮次ID
        tasks: 任务列表
    """
    logger.info(f"处理事件 {event_id} 轮次 {round_id} 的任务组，共 {len(tasks)} 个任务")
    
    # 获取事件信息
    event = Event.query.filter_by(event_id=event_id).first()
    if not event:
        logger.error(f"事件 {event_id} 不存在")
        return
    
    # 构建任务列表文本
    tasks_text = ""
    for i, task in enumerate(tasks, 1):
        tasks_text += f"任务{i}: {task.task_name} (类型: {task.task_type}, ID: {task.task_id})\n"

    tasks_data = []
    for task in tasks:
        tasks_data.append({
            'task_id': task.task_id,
            'task_name': task.task_name,
            'task_type': task.task_type
        })

    request_data = {
        'type': 'generate_actions_by_tasks',
        'req_id': str(uuid.uuid4()),
        'res_id': str(uuid.uuid4()),
        'event_id': event_id,
        'event_round': round_id,
        'event_name': event.event_name,
        'event_message': event.message,
        'tasks': tasks_data
    }
    
    yaml_data = yaml.dump(request_data, allow_unicode=True, default_flow_style=False, indent=2)

    
    # 构建用户提示词
    user_prompt = f"""
```yaml
{yaml_data}
```

分析来自`_captain`的任务要求，生成可供`_operator`操作的具体的`ACTION`。
"""
    logger.info(user_prompt)
    logger.info("--------------------------------")
    # 调用大模型
    prompt_service = PromptService('_manager')
    system_prompt = prompt_service.get_system_prompt()
    logger.info(f"请求大模型：{event_id} - {round_id}")
    create_standard_message(
        event_id=event_id,
        message_from='system',
        round_id=round_id,
        message_type='llm_request',
        content_data="正在请求大模型，理解指挥官任务要求，并进行动作拆分，请耐心等待......"
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
        message_from='_manager',
        round_id=round_id,
        message_type='llm_response',
        content_data=parsed_response
    )
    
    # 处理响应，创建动作
    process_manager_response(parsed_response, tasks)

def process_manager_response(response, tasks):
    """处理管理员响应，创建动作
    
    Args:
        response: 解析后的响应对象
        tasks: 任务列表
    """
    # 获取响应类型
    response_type = response.get('response_type')
    
    # 如果是任务处理
    if response_type == 'ACTION':
        # 获取动作列表
        actions = response.get('actions', [])
        
        # 创建动作
        for action_data in actions:
            # 获取关联的任务
            task_id = action_data.get('task_id')
            task = next((t for t in tasks if t.task_id == task_id), None)
            
            if not task:
                logger.error(f"任务 {task_id} 不存在，大模型返回的任务ID有问题")
                logger.error(f"大模型返回的action: {actions}")
                continue
            
            # 创建动作
            action = Action(
                action_id=str(uuid.uuid4()) ,
                task_id=task.task_id,
                event_id=task.event_id,
                round_id=task.round_id,
                action_name=action_data.get('action_name', ''),
                action_type=action_data.get('action_type', ''),
                action_assignee=action_data.get('action_assignee', '_operator'),
                action_status='pending'
            )
            db.session.add(action)
            
            # 更新任务状态
            task.task_status = 'processing'
            
        db.session.commit()
        logger.info(f"已创建 {len(actions)} 个动作")
    
def run_manager():
    """运行_manager服务"""
    logger.info("启动_manager服务...")
    
    # 导入Flask应用
    from main import app
    
    # 使用应用上下文
    with app.app_context():
        while True:
            try:
                # 获取待处理任务组
                grouped_tasks = get_pending_tasks()
                
                if grouped_tasks:
                    logger.info(f"发现 {len(grouped_tasks)} 组待处理任务")
                    
                    # 处理每组任务
                    for (event_id, round_id), tasks in grouped_tasks.items():
                        process_task_group(event_id, round_id, tasks)
                else:
                    logger.info("没有待处理任务，等待中...")
                    time.sleep(5)
            except Exception as e:
                logger.error(f"处理任务时出错: {e}")
                time.sleep(5) 