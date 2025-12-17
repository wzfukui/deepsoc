import time
import uuid
import json
import traceback
from datetime import datetime
from flask import current_app
from app.models import db, Event, Task, Message, Summary
from app.services.llm_service import call_llm, parse_yaml_response
from app.services.prompt_service import PromptService
from app.utils.message_utils import create_standard_message
from app.utils.mq_utils import RabbitMQPublisher
import yaml
import pika

import logging
logger = logging.getLogger(__name__)


def get_events_to_process():
    """获取待处理的安全事件"""
    return Event.query.filter_by(event_status='pending').order_by(Event.created_at.asc()).first()  

def process_event(event, publisher: RabbitMQPublisher):
    """处理单个安全事件 (Captain: 战略决策层)"""
    logger.info(f"Captain处理事件: {event.event_id} - {event.event_name}")
    
    round_id = event.current_round
    event.event_status = 'processing'
    db.session.commit()

    # 通知前端
    _notify_frontend(publisher, event, 'system', 'llm_request', 
                    {"text": "Captain on the bridge! 正在分析态势并制定作战计划。"})

    # 1. 准备数据
    # 这里我们不需要加载 MCP Tools，因为 Captain 只负责生成 Task，不直接调用工具
    
    request_data = {
        'type': 'generate_tasks_by_event',
        'event_id': event.event_id,
        'round_id': round_id,
        'event_name': event.event_name,
        'message': event.message,
        'context': event.context,
        'source': event.source,
        'severity': event.severity
    }
    
    # 历史任务回顾
    tasks_history_list = []
    history_tasks_query = Task.query.filter_by(event_id=event.event_id).order_by(Task.created_at.desc()).all()
    for task_item in history_tasks_query:
        tasks_history_list.append({
            "task_id": task_item.task_id,
            "task_name": task_item.task_name,
            "task_status": task_item.task_status
        })
    if tasks_history_list:
        request_data['history_tasks'] = tasks_history_list

    yaml_data = yaml.dump(request_data, allow_unicode=True, default_flow_style=False)

    # 上一轮总结
    last_round_summary_content = ""
    if event.current_round > 1:
        last_summary = Summary.query.filter_by(event_id=event.event_id, round_id=round_id-1).first()
        if last_summary:
            last_round_summary_content = f"上一轮战况总结: {last_summary.event_summary}"

    # 2. 调用 LLM
    # Prompt Service 应该返回一个适合生成 Task 的 Prompt
    prompt_service = PromptService('_captain')
    system_prompt = prompt_service.get_system_prompt()
    
    user_prompt = f"""
    {last_round_summary_content}
    
    请根据以下事件信息，分析当前态势，并为下级（_manager）制定下一步的任务清单。
    任务应当是战略性的，例如"调查IP信誉"、"隔离受感染主机"，而不是具体的工具命令。
    
    事件详情 (YAML):
    ```yaml
    {yaml_data}
    ```
    """

    try:
        # Captain 不需要 tools 参数
        response = call_llm(system_prompt, user_prompt)
        
        # 记录 LLM 响应
        _notify_frontend(publisher, event, '_captain', 'llm_response', {"text": response})

        # 3. 解析响应 (YAML)
        parsed_response = parse_yaml_response(response)
        if not parsed_response:
            logger.error("Captain 解析响应失败")
            return

        response_type = parsed_response.get('response_type')
        
        if response_type == 'TASK':
            tasks_data = parsed_response.get('tasks', [])
            for task_detail in tasks_data:
                new_task = Task(
                    task_id=str(uuid.uuid4()),
                    event_id=event.event_id,
                    task_name=task_detail.get('task_name'),
                    task_type=task_detail.get('task_type'),
                    task_assignee=task_detail.get('task_assignee', '_manager'), # 默认给 Manager
                    task_status='pending',
                    round_id=round_id
                )
                db.session.add(new_task)
            
            db.session.commit()
            logger.info(f"Captain Created {len(tasks_data)} tasks.")
            
        elif response_type == 'MISSION_COMPLETE':
            event.event_status = 'completed'
            db.session.commit()
            _notify_frontend(publisher, event, '_captain', 'event_completed', 
                           {"text": "Captain 判定事件处理已完成。", "summary": parsed_response.get('response_text')})

    except Exception as e:
        logger.error(f"Captain 执行出错: {e}")
        traceback.print_exc()

def _notify_frontend(publisher, event, msg_from, msg_type, content_data):
    """辅助函数：发送消息到前端"""
    if not publisher:
        return
    
    msg = create_standard_message(
        event_id=event.event_id,
        message_from=msg_from,
        round_id=event.current_round,
        message_type=msg_type,
        content_data=content_data
    )
    if msg:
        routing_key = f"notifications.frontend.{msg.event_id}.{msg.message_from}.{msg.message_type}"
        try:
            publisher.publish_message(message_body=msg.to_dict(), routing_key=routing_key)
        except Exception as e:
            logger.error(f"发送消息失败: {e}")

def run_captain():
    """运行Captain服务"""
    logger.info("启动Captain服务 (Strategic Mode)...")
    from main import app
    
    publisher = None
    try:
        publisher = RabbitMQPublisher()
        logger.info("RabbitMQ Publisher ready.")
        
        with app.app_context():
            while True:
                try:
                    event = get_events_to_process()
                    if event:
                        process_event(event, publisher)
                        db.session.commit() # 确保事务关闭
                    else:
                        db.session.rollback()
                        time.sleep(5)
                except Exception as e:
                    logger.error(f"Captain Loop Error: {e}")
                    time.sleep(5)
                    
    except Exception as e:
        logger.critical(f"Captain Startup Error: {e}")
    finally:
        if publisher:
            publisher.close()
