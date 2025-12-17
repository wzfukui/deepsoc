import time
import uuid
import json
import traceback
from datetime import datetime
from sqlalchemy import func
from app.models import db, Event, Task, Action, Message, MCPServer, MCPTool
from app.services.llm_service import call_llm, parse_yaml_response
from app.services.prompt_service import PromptService
from app.utils.message_utils import create_standard_message
from app.utils.mq_utils import RabbitMQPublisher
import pika
import yaml
import logging
logger = logging.getLogger(__name__)


def get_pending_tasks():
    """获取待处理的任务，按照event_id和round_id分组"""
    pending_tasks = Task.query.filter_by(task_status='pending').order_by(Task.created_at.asc()).all()
    grouped_tasks = {}
    for task in pending_tasks:
        key = (task.event_id, task.round_id)
        if key not in grouped_tasks:
            grouped_tasks[key] = []
        grouped_tasks[key].append(task)
    return grouped_tasks

def get_available_tools_summary():
    """获取可用工具的摘要列表 (Name/Description only)"""
    # Manager 不需要知道 Schema，只需要知道有什么工具可用
    tools = MCPTool.query.join(MCPServer).filter(MCPServer.status == 'enabled').all()
    summary_lines = []
    for t in tools:
        server_key = t.server.server_key if t.server else "unknown"
        summary_lines.append(f"- {server_key}__{t.name}: {t.description}")
    return "\n".join(summary_lines)

def process_task_group(event_id, round_id, tasks, publisher: RabbitMQPublisher):
    """处理一组任务 (Manager: 战术拆解层)"""
    logger.info(f"Manager处理任务组: Event {event_id}, Round {round_id}, Tasks: {len(tasks)}")
    
    event = Event.query.filter_by(event_id=event_id).first()
    if not event:
        logger.error(f"Event {event_id} not found.")
        return

    # 1. 准备数据
    tasks_data = []
    for task in tasks:
        tasks_data.append({
            'task_id': task.task_id,
            'task_name': task.task_name,
            'task_type': task.task_type
        })

    # 获取工具概览
    tools_summary = get_available_tools_summary()

    request_data = {
        'type': 'generate_actions_by_tasks',
        'event_id': event_id,
        'event_round': round_id,
        'event_name': event.event_name,
        'event_message': event.message,
        'tasks': tasks_data
    }
    
    # 将数据转换为JSON字符串而不是YAML
    json_data = json.dumps(request_data, ensure_ascii=False, indent=2)

    # 2. 构建 Prompt
    prompt_service = PromptService('_manager')
    system_prompt = prompt_service.get_system_prompt()
    
    user_prompt = f"""
    请将以下高层任务拆解为具体的行动 (Action)。
    
    你可用的工具资源如下 (仅供参考，具体调用由 Operator 完成):
    {tools_summary}
    
    如果任务需要调用工具，请生成 action_type='tool_use' 的行动，并在 action_name 中简要描述意图。
    
    任务列表 (JSON):
    ```json
    {json_data}
    ```
    """

    # 3. 调用 LLM
    _notify_frontend(publisher, event_id, round_id, '_manager', 'llm_request', 
                    {"text": f"正在拆解 {len(tasks)} 个任务为具体行动..."})
    
    try:
        # Manager 需要强制使用 json_mode
        response = call_llm(system_prompt, user_prompt, json_mode=True)
        
        # 3. 解析响应 (JSON)
        try:
            parsed_response = json.loads(response)
        except json.JSONDecodeError:
             # 如果直接解析失败，尝试提取代码块中的 JSON
            try:
                if '```json' in response:
                    json_str = response.split('```json')[1].split('```')[0].strip()
                    parsed_response = json.loads(json_str)
                elif '```' in response:
                    json_str = response.split('```')[1].strip()
                    parsed_response = json.loads(json_str)
                else:
                    logger.error(f"Manager 响应无法解析为JSON: {response}")
                    return
            except Exception as e:
                logger.error(f"Manager JSON提取解析失败: {e}")
                return

        if not parsed_response:
            logger.error("Manager 解析 LLM 响应失败")
            return

        _notify_frontend(publisher, event_id, round_id, '_manager', 'llm_response', 
                        {"text": "任务拆解完成。", "details": parsed_response})

        # 4. 处理 Actions
        response_type = parsed_response.get('response_type')
        if response_type == 'ACTION':
            actions_data = parsed_response.get('actions', [])
            created_count = 0
            
            for action_detail in actions_data:
                task_id = action_detail.get('task_id')
                # Find corresponding task
                task = next((t for t in tasks if t.task_id == task_id), None)
                if not task:
                    continue
                
                new_action = Action(
                    action_id=str(uuid.uuid4()),
                    task_id=task.task_id,
                    event_id=task.event_id,
                    round_id=task.round_id,
                    action_name=action_detail.get('action_name'),
                    action_type=action_detail.get('action_type', 'tool_use'),
                    action_assignee=action_detail.get('action_assignee', '_operator'),
                    action_status='pending'
                )
                db.session.add(new_action)
                created_count += 1
                
                # Mark task as processing
                task.task_status = 'processing'
                
            db.session.commit()
            logger.info(f"Manager Created {created_count} Actions.")
            
    except Exception as e:
        logger.error(f"Manager 执行出错: {e}")
        traceback.print_exc()

def _notify_frontend(publisher, event_id, round_id, msg_from, msg_type, content_data):
    if not publisher: return
    msg = create_standard_message(
        event_id=event_id, 
        message_from=msg_from, 
        round_id=round_id, 
        message_type=msg_type, 
        content_data=content_data
    )
    if msg:
        routing_key = f"notifications.frontend.{msg.event_id}.{msg.message_from}.{msg.message_type}"
        try: publisher.publish_message(message_body=msg.to_dict(), routing_key=routing_key)
        except: pass

def run_manager():
    """运行_manager服务"""
    logger.info("启动_manager服务...")
    from main import app # For app_context

    publisher = None
    try:
        publisher = RabbitMQPublisher()
        logger.info("RabbitMQ Publisher for Manager initialized.")

        with app.app_context():
            while True:
                try:
                    grouped_tasks = get_pending_tasks()
                    if grouped_tasks:
                        logger.info(f"Manager发现 {len(grouped_tasks)} 组待处理任务")
                        for (event_id, round_id), tasks in grouped_tasks.items():
                            process_task_group(event_id, round_id, tasks, publisher)
                        try:
                            db.session.commit()
                        except Exception as loop_commit_err:
                            logger.error(f"Manager 主循环提交事务失败: {loop_commit_err}")
                            db.session.rollback()
                    else:
                        db.session.rollback()
                        time.sleep(5)
                except Exception as e:
                    logger.error(f"Manager Error: {e}")
                    time.sleep(5)
    except Exception as e:
        logger.critical(f"Manager Startup Error: {e}")
    finally:
        if publisher: publisher.close()
