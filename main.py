import os
import sys
import argparse
import logging
from flask import Flask, jsonify, render_template, redirect, url_for
from flask_socketio import SocketIO
from flask_migrate import Migrate
from dotenv import load_dotenv
from app.models import db
from app.utils.logging_config import configure_logging

# 配置日志
logger = configure_logging()

# 加载环境变量
load_dotenv()

# 创建Flask应用
app = Flask(__name__, 
            static_folder='app/static',
            template_folder='app/templates')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'deepsoc_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///deepsoc.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化数据库
db.init_app(app)

# 初始化迁移
migrate = Migrate(app, db)

# 初始化SocketIO，添加更多配置选项
socketio = SocketIO(
    app, 
    cors_allowed_origins="*",
    async_mode='threading',  # 使用线程模式
    ping_timeout=60,         # ping超时时间
    ping_interval=25,        # ping间隔
    engineio_logger=True,    # 启用引擎日志以便调试
    logger=True,             # 启用SocketIO日志以便调试
    manage_session=False,    # 不使用Flask会话管理
    always_connect=True,     # 总是允许连接
    max_http_buffer_size=1e8 # 增加HTTP缓冲区大小
)

# 导入路由
from app.controllers.event_controller import event_bp
app.register_blueprint(event_bp, url_prefix='/api/event')

# 导入WebSocket事件处理
from app.controllers.socket_controller import register_socket_events
register_socket_events(socketio)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/warroom/<event_id>')
def warroom(event_id):
    return render_template('warroom.html', event_id=event_id)

@app.route('/health')
def health():
    return jsonify({
        'status': 'success',
        'message': 'DeepSOC API is healthy'
    })

def create_tables():
    """创建所有数据库表"""
    with app.app_context():
        db.create_all()
        logger.info("数据库表创建成功")

def start_agent(role):
    """启动特定角色的Agent"""
    logger.info(f"启动 {role} Agent")
    if role == '_captain':
        from app.services.captain_service import run_captain
        run_captain()
    elif role == '_manager':
        from app.services.manager_service import run_manager
        run_manager()
    elif role == '_operator':
        from app.services.operator_service import run_operator
        run_operator()
    elif role == '_executor':
        from app.services.executor_service import run_executor
        run_executor()
    elif role == '_expert':
        from app.services.expert_service import run_expert
        run_expert()
    else:
        logger.error(f"未知角色: {role}")
        sys.exit(1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='DeepSOC - AI驱动的安全运营中心')
    parser.add_argument('-role', type=str, help='Agent角色: _captain, _manager, _operator, _executor, _expert')
    parser.add_argument('-init', action='store_true', help='初始化数据库')
    args = parser.parse_args()
    
    if args.init:
        create_tables()
    
    if args.role:
        start_agent(args.role)
    else:
        # 启动Web服务器，添加更多选项
        socketio.run(
            app, 
            host=os.getenv('LISTEN_HOST', '0.0.0.0'), 
            port=int(os.getenv('LISTEN_PORT', 5007)), 
            debug=True,
            use_reloader=False,  # 禁用重载器，避免Socket.IO连接问题
            allow_unsafe_werkzeug=True  # 允许在调试模式下使用Werkzeug
        ) 