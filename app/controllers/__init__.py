# 控制器包初始化文件
from app.controllers.event_controller import event_bp
from app.controllers.socket_controller import broadcast_message

__all__ = ['event_bp', 'broadcast_message'] 