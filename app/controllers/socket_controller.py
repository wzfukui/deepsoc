from flask_socketio import emit, join_room, leave_room
from flask import request
from app.models import Message, db, Event
import json
import traceback
from datetime import datetime
import uuid
import logging

# 获取日志记录器
logger = logging.getLogger(__name__)

def register_socket_events(socketio):
    """注册所有WebSocket事件处理函数"""
    
    @socketio.on('connect')
    def handle_connect():
        """处理客户端连接"""
        try:
            logger.info(f"客户端已连接，SID: {request.sid}")
            emit('status', {'status': 'connected'})
        except Exception as e:
            logger.error(f"处理连接时出错: {str(e)}")
            logger.error(traceback.format_exc())
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """处理客户端断开连接"""
        try:
            logger.info(f"客户端已断开连接，SID: {request.sid}")
        except Exception as e:
            logger.error(f"处理断开连接时出错: {str(e)}")
            logger.error(traceback.format_exc())
    
    @socketio.on('join')
    def handle_join(data):
        """处理客户端加入特定作战室"""
        try:
            room = data.get('event_id')
            if room:
                logger.info(f"客户端 {request.sid} 正在尝试加入房间: {room}")
                
                # 加入房间前检查当前房间状态
                try:
                    # 获取当前socketio实例
                    from main import socketio as app_socketio
                    
                    rooms = app_socketio.server.manager.rooms
                    namespace_rooms = rooms.get('/', {})
                    clients = namespace_rooms.get(room, set())
                    logger.info(f"加入前: 房间 {room} 中有 {len(clients)} 个客户端")
                except Exception as e:
                    logger.error(f"检查房间状态时出错: {str(e)}")
                
                # 加入房间
                join_room(room)
                logger.info(f"客户端 {request.sid} 已加入房间: {room}")
                
                # 加入房间后再次检查房间状态
                try:
                    # 获取当前socketio实例
                    from main import socketio as app_socketio
                    
                    rooms = app_socketio.server.manager.rooms
                    namespace_rooms = rooms.get('/', {})
                    clients = namespace_rooms.get(room, set())
                    logger.info(f"加入后: 房间 {room} 中有 {len(clients)} 个客户端")
                    logger.debug(f"房间 {room} 中的客户端: {clients}")
                except Exception as e:
                    logger.error(f"检查房间状态时出错: {str(e)}")
                
                # 发送状态更新
                emit('status', {'status': 'joined', 'event_id': room}, room=room)
                logger.info(f"已发送joined状态到客户端 {request.sid}")
                
                # 发送测试消息
                try:
                    logger.info(f"正在发送WebSocket测试消息到客户端 {request.sid}")
                    
                    # 直接发送到当前客户端
                    emit('test_message', {
                        'message': '这是一条测试消息，用于验证WebSocket连接',
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    # 发送到整个房间
                    emit('test_message', {
                        'message': f'客户端 {request.sid} 已加入房间 {room}',
                        'timestamp': datetime.now().isoformat()
                    }, room=room)
                    
                    logger.info(f"测试消息已发送")
                except Exception as e:
                    logger.error(f"发送测试消息时出错: {str(e)}")
            else:
                logger.warning(f"客户端 {request.sid} 尝试加入房间但未提供event_id")
                emit('error', {'message': '缺少event_id参数'})
        except Exception as e:
            logger.error(f"处理加入房间时出错: {str(e)}")
            logger.error(traceback.format_exc())
    
    @socketio.on('leave')
    def handle_leave(data):
        """处理客户端离开特定作战室"""
        try:
            room = data.get('event_id')
            if room:
                leave_room(room)
                logger.info(f"客户端已离开房间: {room}")
                emit('status', {'status': 'left', 'event_id': room}, room=room)
        except Exception as e:
            logger.error(f"处理离开房间时出错: {str(e)}")
            logger.error(traceback.format_exc())
    
    @socketio.on('message')
    def handle_message(data):
        """处理客户端发送的消息"""
        try:
            event_id = data.get('event_id')
            message_content = data.get('message')
            sender = data.get('sender', 'user')
            
            if not event_id or not message_content:
                emit('error', {'message': '缺少必要参数'})
                return
            
            # 查找事件
            event = Event.query.filter_by(event_id=event_id).first()
            if not event:
                emit('error', {'message': '事件不存在'})
                return
            
            # 创建消息
            message = Message(
                message_id=str(uuid.uuid4()),
                event_id=event_id,
                message_from=sender,
                message_type='user_message',
                message_content=message_content
            )
            
            # 保存消息
            db.session.add(message)
            db.session.commit()
            
            # 广播消息
            emit('new_message', message.to_dict(), room=event_id)
            
            # 触发AI响应
            trigger_ai_response(event_id, message)
        except Exception as e:
            logger.error(f"处理消息时出错: {str(e)}")
            logger.error(traceback.format_exc())
            emit('error', {'message': f'处理消息时出错: {str(e)}'})
    
    @socketio.on('test_connection')
    def handle_test_connection(data):
        """处理客户端发送的测试连接请求"""
        try:
            event_id = data.get('event_id')
            timestamp = data.get('timestamp')
            
            logger.info(f"收到客户端 {request.sid} 的连接测试请求: event_id={event_id}, timestamp={timestamp}")
            
            # 发送响应
            emit('test_connection_response', {
                'message': '连接测试成功',
                'timestamp': datetime.now().isoformat(),
                'request_timestamp': timestamp
            })
            
            # 如果提供了事件ID，还发送一条新消息
            if event_id:
                # 创建测试消息
                test_message = Message(
                    message_id=str(uuid.uuid4()),
                    event_id=event_id,
                    message_from='system',
                    message_type='system_notification',
                    message_content={
                        "type": "system_notification",
                        "timestamp": datetime.now().isoformat(),
                        "data": {
                            "response_text": f"这是一条通过WebSocket发送的测试系统通知 (SID: {request.sid})"
                        }
                    }
                )
                
                # 广播测试消息
                broadcast_message(test_message)
        except Exception as e:
            logger.error(f"处理测试连接请求时出错: {str(e)}")
            logger.error(traceback.format_exc())
            emit('error', {'message': f'处理测试连接请求时出错: {str(e)}'})

def broadcast_message(message):
    """广播消息到特定作战室
    
    Args:
        message: Message对象
    """
    try:
        from main import socketio
        
        # 通过WebSocket推送消息
        event_id = message.event_id
        message_dict = message.to_dict()
        
        # 保存到数据库（如果尚未保存）
        if message.id is None:
            db.session.add(message)
            db.session.commit()
        
        logger.info(f"准备广播消息: ID={message.id}, 类型={message.message_type}, 来源={message.message_from}, 事件={event_id}")
        
        # 添加更详细的消息内容日志（但避免日志过大）
        if isinstance(message.message_content, dict):
            content_preview = str(message.message_content)[:200] + "..." if len(str(message.message_content)) > 200 else str(message.message_content)
            logger.debug(f"消息内容预览: {content_preview}")
        
        # 检查socketio是否可用
        if not socketio:
            logger.error("socketio对象不可用，无法广播消息")
            return
            
        # 检查房间是否有连接的客户端
        try:
            # 尝试获取房间中的客户端数量
            rooms = socketio.server.manager.rooms
            logger.debug(f"所有房间: {rooms}")
            
            # 安全地获取客户端数量
            namespace_rooms = rooms.get('/', {})
            clients = namespace_rooms.get(event_id, set())
            clients_count = len(clients)
            
            logger.info(f"房间 {event_id} 中有 {clients_count} 个连接的客户端")
            if clients_count == 0:
                logger.warning(f"警告: 房间 {event_id} 中没有连接的客户端，消息可能无法送达")
                # 如果没有客户端，仍然保存消息到数据库，但不尝试广播
                return
        except Exception as e:
            logger.error(f"获取房间客户端数量时出错: {str(e)}")
        
        # 尝试广播消息 - 方法1：使用socketio.emit
        logger.info(f"方法1: 正在通过socketio.emit广播消息到房间: {event_id}, 事件名称: new_message")
        socketio.emit('new_message', message_dict, room=event_id)
        logger.info(f"方法1: 消息已通过socketio.emit广播")
        
        # 尝试广播消息 - 方法2：使用socketio.server.emit
        try:
            logger.info(f"方法2: 正在通过socketio.server.emit广播消息到房间: {event_id}")
            socketio.server.emit('new_message', message_dict, room=event_id, namespace='/')
            logger.info(f"方法2: 消息已通过socketio.server.emit广播")
        except Exception as e:
            logger.error(f"方法2广播消息时出错: {str(e)}")
        
        # 尝试广播消息 - 方法3：直接向每个客户端发送
        try:
            if clients_count > 0:
                logger.info(f"方法3: 正在直接向 {clients_count} 个客户端发送消息")
                for client_sid in clients:
                    logger.info(f"向客户端 {client_sid} 发送消息")
                    socketio.emit('new_message', message_dict, room=client_sid)
                logger.info(f"方法3: 已向所有客户端发送消息")
        except Exception as e:
            logger.error(f"方法3广播消息时出错: {str(e)}")
        
        # 如果状态发生变化，发送状态更新
        if message.message_type in ['event_summary', 'llm_response']:
            # 获取事件
            event = Event.query.filter_by(event_id=event_id).first()
            if event:
                logger.info(f"发送事件状态更新: 事件={event_id}, 状态={event.status}, 轮次={event.current_round}")
                socketio.emit('status', {
                    'event_status': event.status,
                    'event_round': event.current_round
                }, room=event_id)
    except Exception as e:
        logger.error(f"广播消息时出错: {str(e)}")
        logger.error(traceback.format_exc())

def trigger_ai_response(event_id, user_message):
    """触发AI响应
    
    Args:
        event_id: 事件ID
        user_message: 用户消息对象
    """
    try:
        # 这里可以添加触发AI响应的逻辑
        # 例如，可以将消息放入队列，由AI Agent处理
        logger.info(f"收到用户消息，事件ID: {event_id}, 消息内容: {user_message.message_content}")
        
        # 在实际项目中，这里应该触发AI Agent的处理流程
        # 以下代码仅作为示例，实际应用中应该由AI Agent生成响应
        
        # 创建AI回复消息
        ai_message = Message(
            message_id=str(uuid.uuid4()),
            event_id=event_id,
            message_from='_captain',  # 由安全指挥官回复
            message_type='llm_response',
            message_content={
                "type": "llm_response",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "response_type": "ROGER",
                    "response_text": f"收到您的消息: {user_message.message_content}\n\n我们正在处理中，请稍候..."
                }
            }
        )
        
        # 广播AI回复
        broadcast_message(ai_message)
    except Exception as e:
        logger.error(f"触发AI响应时出错: {str(e)}")
        logger.error(traceback.format_exc()) 

def broadcast_execution_update(execution):
    """广播执行任务状态更新"""
    try:
        # 获取当前socketio实例
        from main import socketio
        
        socketio.emit('execution_update', {
            'execution_id': execution.execution_id,
            'status': execution.execution_status,
            'updated_at': execution.updated_at.isoformat()
        }, room=execution.event_id)
        
        logger.info(f"已广播执行任务状态更新: {execution.execution_id}, 状态: {execution.execution_status}")
    except Exception as e:
        logger.error(f"广播执行任务状态更新时出错: {str(e)}")
        logger.error(traceback.format_exc())