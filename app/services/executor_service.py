import time
import uuid
import json
from datetime import datetime
from flask import current_app
from sqlalchemy import func
from app.models import db, Event, Task, Action, Command, Execution, Message
from app.controllers.socket_controller import broadcast_message
from app.mcp import MCPManager
from app.utils.message_utils import create_standard_message
from app.services.llm_service import call_llm
import logging

logger = logging.getLogger(__name__)

def get_pending_commands():
    """获取待处理的命令"""
    # 优先处理 mcp_tool 类型的命令
    return Command.query.filter_by(command_status='pending').order_by(Command.created_at.asc()).all()

def process_command(command):
    """处理单个命令 (Executor: 动作执行层)"""
    logger.info(f"Executor处理命令: {command.command_id}, 类型: {command.command_type}")
    
    command.command_status = 'processing'
    db.session.commit()
    
    result = None
    
    try:
        if command.command_type == 'mcp_tool':
            result = execute_mcp_tool(command)
        elif command.command_type == 'manual':
            result = handle_manual_command(command)
        else:
            result = {"status": "failed", "message": f"Unknown command type: {command.command_type}"}
        
        # 结果处理与摘要
        if result.get('status') == 'success':
            command.command_status = 'completed'
            command.command_result = result.get('data', {})
            update_action_status(command.action_id, 'completed')
        else:
            command.command_status = 'failed'
            command.command_result = {"error": result.get('message')}
            update_action_status(command.action_id, 'failed')
        
        db.session.commit()
        
        # 发送通知
        create_command_message(command, result)
        
    except Exception as e:
        logger.error(f"Executor Error: {e}")
        command.command_status = 'failed'
        command.command_result = {"error": str(e)}
        update_action_status(command.action_id, 'failed')
        db.session.commit()
        create_command_message(command, {"status": "failed", "message": str(e)})

def execute_mcp_tool(command):
    """执行 MCP 工具并生成摘要"""
    params = command.command_params or {}
    tool_name = params.get('tool_name')
    arguments = params.get('arguments', {})
    
    if not tool_name:
        return {"status": "failed", "message": "Missing tool_name in command params"}

    logger.info(f"正在通过 MCP 调用工具: {tool_name}, Args: {arguments}")
    
    # 1. 实际执行
    try:
        # execute_tool_sync 返回 {"result": "...", "error": "..."}
        raw_output = MCPManager.execute_tool_sync(tool_name, arguments)
    except Exception as e:
        return {"status": "failed", "message": f"MCP Client Error: {e}"}

    if "error" in raw_output:
        return {"status": "failed", "message": raw_output["error"]}
    
    output_text = raw_output.get("result", "")
    
    # 2. 结果摘要 (如果不长，直接返回；如果太长，调用 LLM 摘要)
    summary = output_text
    if len(output_text) > 2000:
        logger.info("工具输出过长，正在生成摘要...")
        try:
            prompt = f"请总结以下工具执行日志的关键信息，保留核心发现（如IP、端口、漏洞、报错原因），去除冗余信息。\n\n日志:\n{output_text[:10000]}"
            summary = call_llm(system_prompt="你是一个日志分析专家。", user_prompt=prompt, long_text=True)
        except Exception as e:
            logger.warning(f"摘要生成失败: {e}")
            summary = output_text[:2000] + "\n...(Summary failed, truncated)..."

    # 3. 记录 Execution
    execution = Execution(
        execution_id=str(uuid.uuid4()),
        command_id=command.command_id,
        action_id=command.action_id,
        task_id=command.task_id,
        event_id=command.event_id,
        round_id=command.round_id,
        execution_result=output_text, # 原始结果存库（如果数据库支持大字段）
        execution_summary=summary,     # 摘要用于 Context
        execution_status="success"
    )
    db.session.add(execution)
    
    return {
        "status": "success",
        "data": {
            "summary": summary,
            "execution_id": execution.execution_id
        }
    }

def handle_manual_command(command):
    """处理人工命令 (保持原有逻辑)"""
    logger.info(f"处理人工命令: {command.command_id}")
    execution = Execution(
        execution_id=str(uuid.uuid4()),
        command_id=command.command_id,
        action_id=command.action_id,
        task_id=command.task_id,
        event_id=command.event_id,
        round_id=command.round_id,
        execution_summary="等待人工处理",
        execution_status="waiting"
    )
    db.session.add(execution)
    
    return {
        "status": "success",
        "message": "命令已提交，等待人工处理",
        "data": {"execution_id": execution.execution_id}
    }

def update_action_status(action_id, status):
    action = Action.query.filter_by(action_id=action_id).first()
    if action:
        action.action_status = status

def create_command_message(command, result):
    content_data = {
        "command_id": command.command_id,
        "command_type": command.command_type,
        "command_name": command.command_name,
        "status": command.command_status,
        "result": command.command_result
    }
    create_standard_message(
        event_id=command.event_id,
        message_from='_executor',
        round_id=command.round_id,
        message_type='command_result',
        content_data=content_data
    )

def run_executor():
    """运行_executor服务"""
    logger.info("启动_executor服务...")
    from main import app
    with app.app_context():
        while True:
            try:
                pending_commands = get_pending_commands()
                if pending_commands:
                    logger.info(f"发现 {len(pending_commands)} 个待处理命令")
                    for command in pending_commands:
                        process_command(command)
                    try:
                        db.session.commit()
                    except Exception as loop_commit_err:
                        logger.error(f"Executor 主循环提交事务失败: {loop_commit_err}")
                        db.session.rollback()
                else:
                    db.session.rollback()
                    time.sleep(5)
            except Exception as e:
                logger.error(f"Executor Error: {e}")
                time.sleep(5)
