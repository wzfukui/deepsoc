import time
import uuid
import json
import traceback
from datetime import datetime
from sqlalchemy import func
from app.models import db, Event, Task, Action, Command, Message, MCPServer, MCPTool
from app.services.llm_service import call_llm
from app.mcp.client_manager import mcp_manager
from app.utils.message_utils import create_standard_message
from app.utils.mq_utils import RabbitMQPublisher
import pika
import yaml
import logging
logger = logging.getLogger(__name__)

def get_pending_actions():
    """获取待处理的动作，按照event_id和round_id分组"""
    pending_actions = Action.query.filter_by(action_status='pending').order_by(Action.created_at.asc()).all()
    grouped_actions = {}
    for action in pending_actions:
        key = (action.event_id, action.round_id)
        if key not in grouped_actions:
            grouped_actions[key] = []
        grouped_actions[key].append(action)
    return grouped_actions

def process_action_group(event_id, round_id, actions, publisher: RabbitMQPublisher):
    """处理一组动作 (Operator: 工具编排层)"""
    logger.info(f"Operator处理动作组: Event {event_id}, Round {round_id}, Actions: {len(actions)}")
    
    event = Event.query.filter_by(event_id=event_id).first()
    if not event:
        logger.error(f"Event {event_id} not found.")
        return

    # 1. 加载工具定义
    # Operator 需要完整的 Schema 来生成正确的工具调用
    # 使用新的 Client Manager 获取工具定义
    from app.mcp.client_manager import mcp_manager
    tools = mcp_manager.get_all_tools_definitions()

    # 2. 逐个处理 Action
    # 因为 LLM Function Calling 一次处理一个 Context 更准确，这里我们不再批量生成，而是逐个 Action 询问
    for action in actions:
        try:
            process_single_action(event, action, tools, publisher)
        except Exception as e:
            logger.error(f"处理 Action {action.action_id} 失败: {e}")
            action.action_status = 'error'
            db.session.commit()

def process_single_action(event, action, tools, publisher):
    """处理单个 Action，将其转化为具体的 Tool Call Command"""
    logger.info(f"正在编排 Action: {action.action_name}")
    
    # 获取关联的任务信息
    task = Task.query.filter_by(task_id=action.task_id).first()
    task_context = f"所属任务: {task.task_name}" if task else ""

    # System Prompt
    system_prompt = """你是一个安全运营工程师（Operator）。你的职责是将上级（Manager）发布的行动指令转化为具体的工具调用（Command）。
你拥有以下 MCP 工具集。请根据 Action 的意图，选择最合适的工具，并生成准确的调用参数。
如果现有工具无法满足需求，请如实告知。
"""
    
    user_prompt = f"""
    事件背景: {event.event_name}
    {task_context}
    
    当前行动 (Action):
    名称: {action.action_name}
    类型: {action.action_type}
    
    请选择一个合适的工具来执行此行动。
    """

    _notify_frontend(publisher, event.event_id, action.round_id, '_operator', 'llm_request', 
                    {"text": f"正在为行动 '{action.action_name}' 匹配合适的 MCP 工具..."})

    try:
        # 调用 LLM (开启 Tool Call)
        response_msg = call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            tools=tools if tools else None,
            tool_choice="auto" if tools else None
        )
        
        content = response_msg.content if hasattr(response_msg, 'content') else str(response_msg)
        tool_calls = getattr(response_msg, 'tool_calls', None)

        if tool_calls:
            # LLM 选择了工具 -> 生成 Command
            for tool_call in tool_calls:
                func_name = tool_call.function.name
                func_args_str = tool_call.function.arguments
                
                try:
                    func_args = json.loads(func_args_str)
                except:
                    func_args = {}

                new_command = Command(
                    command_id=str(uuid.uuid4()),
                    command_type='mcp_tool', # 新类型
                    command_name=f"Call {func_name}",
                    command_assignee='_executor',
                    action_id=action.action_id,
                    task_id=action.task_id,
                    round_id=action.round_id,
                    event_id=action.event_id,
                    command_params={
                        "tool_name": func_name,
                        "arguments": func_args
                    },
                    command_status='pending'
                )
                db.session.add(new_command)
                
                _notify_frontend(publisher, event.event_id, action.round_id, '_operator', 'command_created', 
                                {"text": f"已生成工具调用指令: {func_name}", "args": func_args})

            action.action_status = 'processing'
            db.session.commit()
            
        else:
            # LLM 没有选择工具，可能是没有合适的工具，或者是纯文本回复
            logger.warning(f"Operator 未能为 Action {action.action_name} 匹配到工具。LLM回复: {content}")
            action.action_status = 'manual_required' # 标记为需要人工介入
            # 记录一条消息解释原因
            _notify_frontend(publisher, event.event_id, action.round_id, '_operator', 'error_no_tool', 
                           {"text": f"未能匹配到自动化工具，请人工处理。AI建议: {content}"})
            db.session.commit()

    except Exception as e:
        logger.error(f"Operator LLM Error: {e}")
        raise e

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

def run_operator():
    """运行_operator服务"""
    logger.info("启动_operator服务...")
    from main import app

    publisher = None
    try:
        publisher = RabbitMQPublisher()
        logger.info("RabbitMQ Publisher for Operator initialized.")
        with app.app_context():
            while True:
                try:
                    grouped_actions = get_pending_actions()
                    if grouped_actions:
                        logger.info(f"Operator发现 {len(grouped_actions)} 组待处理动作")
                        for (event_id, round_id), actions in grouped_actions.items():
                            process_action_group(event_id, round_id, actions, publisher)
                            try:
                                db.session.commit()
                            except Exception as loop_commit_err:
                                logger.error(f"Operator 主循环提交事务失败: {loop_commit_err}")
                                db.session.rollback()
                    else:
                        db.session.rollback()
                        time.sleep(5)
                except Exception as e:
                    logger.error(f"Operator Error: {e}")
                    time.sleep(5)
    except Exception as e:
        logger.critical(f"Operator Startup Error: {e}")
    finally:
        if publisher: publisher.close()
