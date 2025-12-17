import time
import uuid
import json
import traceback
from datetime import datetime
from flask import current_app
from app.models import db, Event, Task, Message, Summary
from app.services.llm_service import call_llm
from app.mcp import MCPManager
from app.utils.message_utils import create_standard_message
from app.utils.mq_utils import RabbitMQPublisher
import pika

import logging
logger = logging.getLogger(__name__)


def get_events_to_process():
    """获取待处理的安全事件"""
    return Event.query.filter_by(event_status='pending').order_by(Event.created_at.asc()).first()  

def process_event(event, publisher: RabbitMQPublisher):
    """处理单个安全事件 (MCP Enhanced Version)"""
    logger.info(f"Captain处理事件: {event.event_id} - {event.event_name}")
    
    # 初始化
    round_id = event.current_round
    event.event_status = 'processing'
    db.session.commit()

    # 通知前端: AI开始介入
    _notify_frontend(publisher, event, 'system', 'llm_request', 
                    {"text": "Captain on the bridge! 正在请求AI指挥官调用MCP工具进行分析。"})

    # 1. 获取所有可用 MCP 工具
    tools = MCPManager.get_all_tool_definitions()
    logger.info(f"可用工具数量: {len(tools)}")

    # 2. 构建对话历史
    # System Prompt 简洁化
    system_prompt = """你是一个高级安全运营指挥官（Captain）。你的任务是分析安全事件，并利用一切可用的工具来调查、取证和响应。
你拥有通过 MCP (Model Context Protocol) 调用的工具集。
- 请根据事件信息，自主决定调用哪些工具。
- 分析工具的输出，如果需要更多信息，继续调用工具。
- 如果认为事件已处理完毕或有了明确结论，请给出最终的分析报告。
不要输出YAML格式，直接以自然语言回复，或者发起工具调用。
"""

    # User Prompt 包含事件详情
    event_context = f"""
    事件ID: {event.event_id}
    事件名称: {event.event_name}
    描述: {event.message}
    上下文: {event.context}
    来源: {event.source}
    严重性: {event.severity}
    """
    
    # 历史对话记录 (如果不是第一轮，可以加载之前的 Summary)
    history = []
    if event.current_round > 1:
        last_summary = Summary.query.filter_by(event_id=event.event_id, round_id=round_id-1).first()
        if last_summary:
            history.append({"role": "assistant", "content": f"上一轮总结: {last_summary.event_summary}"})

    # 3. 进入 LLM 思考 Loop (支持多次 Tool Call)
    max_steps = 10
    current_step = 0
    
    # 初始 Prompt
    current_messages = [
        {"role": "user", "content": f"请分析以下安全事件并采取行动：\n{event_context}"}
    ]

    while current_step < max_steps:
        current_step += 1
        logger.info(f"LLM Step {current_step}/{max_steps}")

        # 调用 LLM
        try:
            # 注意：history 参数是用来传之前的 round 对话的，这里我们将 current_messages 作为 context 传递
            # 因为 call_llm 的设计是把 system_prompt + history + user_prompt 拼起来
            # 这里我们需要灵活一点。为了复用 call_llm，我们将 current_messages 拆分
            
            # 实际上 call_llm 的 history 参数期望 list of dicts.
            # 我们可以把 current_messages 全部传给 history (除了最后一个作为 user_prompt? 不，call_llm 会 append user_prompt)
            # 让我们稍微 hack 一下 call_llm 的用法：
            # system_prompt 传进去
            # user_prompt 传空字符串 (如果 current_messages 已经包含了用户请求)
            # history 传 current_messages
            
            response_msg = call_llm(
                system_prompt=system_prompt,
                user_prompt="", 
                history=current_messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None
            )
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            _notify_frontend(publisher, event, '_captain', 'error_internal', {"text": f"LLM调用失败: {str(e)}"})
            event.event_status = 'error_processing'
            db.session.commit()
            return

        # 检查响应类型
        # 如果是 str，说明是纯文本回复 -> 结束
        # 如果是 Message 对象且有 tool_calls -> 执行工具
        
        content = response_msg.content if hasattr(response_msg, 'content') else response_msg
        tool_calls = getattr(response_msg, 'tool_calls', None)

        # 记录 Assistant 回复到 history
        current_messages.append(response_msg) # response_msg 是 ChatCompletionMessage 对象，可以直接作为 history item (OpenAI SDK handle this)

        # 通知前端 Assistant 的思考/文本
        if content:
            _notify_frontend(publisher, event, '_captain', 'llm_response', {"text": content})
            logger.info(f"LLM回复: {content[:100]}...")

        if tool_calls:
            logger.info(f"LLM发起 {len(tool_calls)} 个工具调用")
            
            for tool_call in tool_calls:
                func_name = tool_call.function.name
                func_args_str = tool_call.function.arguments
                call_id = tool_call.id
                
                try:
                    func_args = json.loads(func_args_str)
                except:
                    func_args = {}
                
                logger.info(f"执行工具: {func_name}, 参数: {func_args}")
                _notify_frontend(publisher, event, '_captain', 'tool_execution', 
                                {"text": f"正在执行工具: {func_name}", "args": func_args})

                # 执行工具
                tool_result = MCPManager.execute_tool_sync(func_name, func_args)
                result_str = json.dumps(tool_result, ensure_ascii=False)
                
                # 记录 Tool Output 到 history
                current_messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": result_str
                })
                
                logger.info(f"工具执行结果长度: {len(result_str)}")
                _notify_frontend(publisher, event, '_executor', 'tool_result', 
                                {"text": f"工具 {func_name} 执行完成", "result": tool_result})
            
            # 继续下一轮 Loop，把 Tool Outputs 带给 LLM
            continue
        else:
            # 没有 Tool Calls，说明 LLM 完成了回复
            logger.info("LLM结束思考，任务完成")
            break

    # 4. 结束处理
    event.event_status = 'completed'
    
    # 创建 Summary (简单取最后一次回复)
    summary_text = content if content else "处理完成 (无文本总结)"
    
    summary = Summary(
        summary_id=str(uuid.uuid4()),
        event_id=event.event_id,
        round_id=round_id,
        event_summary=summary_text,
        event_suggestion="无"
    )
    db.session.add(summary)
    db.session.commit()

    _notify_frontend(publisher, event, '_captain', 'event_completed', 
                    {"text": "事件分析处理已完成。", "summary": summary_text})


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
    logger.info("启动Captain服务 (MCP Enhanced)...")
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
                        db.session.commit()
                    else:
                        db.session.rollback()
                        time.sleep(5)
                except Exception as e:
                    logger.error(f"Captain Loop Error: {e}")
                    logger.error(traceback.format_exc())
                    time.sleep(5)
                    
    except Exception as e:
        logger.critical(f"Captain Startup Error: {e}")
    finally:
        if publisher:
            publisher.close()
