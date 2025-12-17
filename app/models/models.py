     1|from datetime import datetime
     2|import uuid
     3|from flask_sqlalchemy import SQLAlchemy
     4|from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, func
     5|from werkzeug.security import generate_password_hash, check_password_hash
     6|
     7|db = SQLAlchemy()
     8|
     9|class User(db.Model):
    10|    """用户表"""
    11|    __tablename__ = "users"
    12|
    13|    id = Column(Integer, primary_key=True, autoincrement=True)
    14|    user_id = db.Column(db.String(64), default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    15|    username = db.Column(db.String(64), nullable=False, unique=True)
    16|    nickname = db.Column(db.String(64))
    17|    email = db.Column(db.String(120), nullable=False, unique=True)
    18|    phone = db.Column(db.String(32))
    19|    password_hash = db.Column(db.String(256), nullable=False)
    20|    role = db.Column(db.String(32), default='user')  # admin, user
    21|    last_login_at = db.Column(db.DateTime)
    22|    is_active = db.Column(db.Boolean, default=True)
    23|    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    24|    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    25|    
    26|    def set_password(self, password):
    27|        self.password_hash = generate_password_hash(password)
    28|        
    29|    def check_password(self, password):
    30|        return check_password_hash(self.password_hash, password)
    31|    
    32|    def to_dict(self):
    33|        return {
    34|            'id': self.id,
    35|            'user_id': self.user_id,
    36|            'username': self.username,
    37|            'nickname': self.nickname,
    38|            'email': self.email,
    39|            'phone': self.phone,
    40|            'role': self.role,
    41|            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
    42|            'is_active': self.is_active,
    43|            'created_at': self.created_at.isoformat() if self.created_at else None,
    44|            'updated_at': self.updated_at.isoformat() if self.updated_at else None
    45|        }
    46|
    47|class Event(db.Model):
    48|    """安全事件表"""
    49|    __tablename__ = "events"
    50|
    51|    id = Column(Integer, primary_key=True, autoincrement=True)
    52|    event_id = db.Column(db.String(64), nullable=False, unique=True)
    53|    event_name = db.Column(db.String(256))
    54|    message = db.Column(db.Text)
    55|    context = db.Column(db.Text)
    56|    source = db.Column(db.String(64))
    57|    severity = db.Column(db.String(32))
    58|    event_status = db.Column(db.String(32), default='pending')
    59|    current_round = db.Column(db.Integer, default=1)  # 当前处理轮次，默认为1
    60|    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    61|    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    62|    
    63|    def to_dict(self):
    64|        return {
    65|            'id': self.id,
    66|            'event_id': self.event_id,
    67|            'event_name': self.event_name,
    68|            'message': self.message,
    69|            'context': self.context,
    70|            'source': self.source,
    71|            'severity': self.severity,
    72|            'event_status': self.event_status,
    73|            'status': self.event_status,  # backward compatibility
    74|            'current_round': self.current_round,
    75|            'created_at': self.created_at.isoformat() if self.created_at else None,
    76|            'updated_at': self.updated_at.isoformat() if self.updated_at else None
    77|        }
    78|
    79|class Task(db.Model):
    80|    """任务表"""
    81|    __tablename__ = 'tasks'
    82|    
    83|    id = Column(Integer, primary_key=True, autoincrement=True)
    84|    task_id = db.Column(db.String(64), nullable=False, unique=True)
    85|    event_id = db.Column(db.String(64))  # 关联的事件ID
    86|    task_name = db.Column(db.String(256))
    87|    task_type = db.Column(db.String(64))  # query, write, notify
    88|    task_assignee = db.Column(db.String(64))
    89|    task_status = db.Column(db.String(32), default='pending')
    90|    round_id = db.Column(db.Integer)
    91|    result = db.Column(db.JSON)
    92|    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    93|    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    94|    
    95|    def to_dict(self):
    96|        return {
    97|            'id': self.id,
    98|            'task_id': self.task_id,
    99|            'event_id': self.event_id,
   100|            'task_name': self.task_name,
   101|            'task_type': self.task_type,
   102|            'task_assignee': self.task_assignee,
   103|            'task_status': self.task_status,
   104|            'round_id': self.round_id,
   105|            'result': self.result,
   106|            'created_at': self.created_at.isoformat() if self.created_at else None,
   107|            'updated_at': self.updated_at.isoformat() if self.updated_at else None
   108|        }
   109|
   110|class Action(db.Model):
   111|    """动作表"""
   112|    __tablename__ = 'actions'
   113|
   114|    id = Column(Integer, primary_key=True, autoincrement=True)
   115|    action_id = db.Column(db.String(64), nullable=False, unique=True)
   116|    task_id = db.Column(db.String(64))  # 关联的任务ID
   117|    round_id = db.Column(db.Integer)
   118|    event_id = db.Column(db.String(64))  # 关联的事件ID
   119|    action_name = db.Column(db.String(256))
   120|    action_type = db.Column(db.String(64))
   121|    action_assignee = db.Column(db.String(64))
   122|    action_status = db.Column(db.String(32), default='pending')
   123|    action_result = db.Column(db.JSON)
   124|    created_at = db.Column(db.DateTime, default=datetime.utcnow)
   125|    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
   126|    
   127|    def to_dict(self):
   128|        return {
   129|            'id': self.id,
   130|            'action_id': self.action_id,
   131|            'task_id': self.task_id,
   132|            'event_id': self.event_id,
   133|            'round_id': self.round_id, 
   134|            'action_name': self.action_name,
   135|            'action_type': self.action_type,
   136|            'action_assignee': self.action_assignee,
   137|            'action_status': self.action_status,
   138|            'action_result': self.action_result,
   139|            'created_at': self.created_at.isoformat() if self.created_at else None,
   140|            'updated_at': self.updated_at.isoformat() if self.updated_at else None
   141|        }
   142|
   143|class Command(db.Model):
   144|    """命令表"""
   145|    __tablename__ = 'commands'
   146|    
   147|    id = Column(Integer, primary_key=True, autoincrement=True)
   148|    command_id = db.Column(db.String(64), nullable=False, unique=True)
   149|    action_id = db.Column(db.String(64))  # 关联的动作ID
   150|    task_id = db.Column(db.String(64))  # 关联的任务ID
   151|    event_id = db.Column(db.String(64))  # 关联的事件ID
   152|    round_id = db.Column(db.Integer)
   153|    command_name = db.Column(db.String(256))
   154|    command_type = db.Column(db.String(64))
   155|    command_assignee = db.Column(db.String(64))
   156|    command_entity = db.Column(db.JSON)
   157|    command_params = db.Column(db.JSON)
   158|    command_status = db.Column(db.String(32), default='pending')
   159|    command_result = db.Column(db.JSON)
   160|    created_at = db.Column(db.DateTime, default=datetime.utcnow)
   161|    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
   162|    
   163|    def to_dict(self):
   164|        return {
   165|            'id': self.id,
   166|            'command_id': self.command_id,
   167|            'action_id': self.action_id,
   168|            'task_id': self.task_id,
   169|            'event_id': self.event_id,
   170|            'round_id': self.round_id,
   171|            'command_name': self.command_name,
   172|            'command_type': self.command_type,
   173|            'command_entity': self.command_entity,
   174|            'command_params': self.command_params,
   175|            'command_status': self.command_status,
   176|            'command_result': self.command_result,
   177|            'created_at': self.created_at.isoformat() if self.created_at else None,
   178|            'updated_at': self.updated_at.isoformat() if self.updated_at else None
   179|        }
   180|
   181|class Execution(db.Model):
   182|    """执行表"""
   183|    __tablename__ = 'executions'
   184|    
   185|    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
   186|    execution_id = db.Column(db.String(48), nullable=False, unique=True)
   187|    command_id = db.Column(db.String(48))
   188|    action_id = db.Column(db.String(48))
   189|    task_id = db.Column(db.String(48))
   190|    event_id = db.Column(db.String(48))
   191|    round_id = db.Column(db.Integer)
   192|    execution_result = db.Column(db.Text)
   193|    execution_summary = db.Column(db.Text)
   194|    ai_summary = db.Column(db.Text)
   195|    execution_status = db.Column(db.String(50), default='pending')
   196|    created_at = db.Column(db.DateTime, default=datetime.utcnow)
   197|    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
   198|
   199|    def to_dict(self):
   200|        return {
   201|            'id': self.id,
   202|            'execution_id': self.execution_id,
   203|            'command_id': self.command_id,
   204|            'action_id': self.action_id,
   205|            'task_id': self.task_id,
   206|            'event_id': self.event_id,
   207|            'round_id': self.round_id,
   208|            'execution_result': self.execution_result,
   209|            'execution_summary': self.execution_summary,
   210|            'ai_summary': self.ai_summary,
   211|            'execution_status': self.execution_status,
   212|            'created_at': self.created_at.isoformat() if self.created_at else None,
   213|            'updated_at': self.updated_at.isoformat() if self.updated_at else None
   214|        }
   215|
   216|class Message(db.Model):
   217|    """消息表"""
   218|    __tablename__ = 'messages'
   219|    
   220|    id = Column(Integer, primary_key=True, autoincrement=True)
   221|    message_id = Column(String(64), default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
   222|    event_id = Column(String(64))  # 关联的事件ID
   223|    user_id = Column(String(64))
   224|    message_from = Column(String(64))
   225|    round_id = db.Column(db.Integer)
   226|    message_content = Column(JSON)
   227|    message_type = Column(String(32))
   228|    # 工程师对话相关字段
   229|    message_category = Column(String(32), default='agent')  # 'agent' or 'engineer_chat'
   230|    chat_session_id = Column(String(64))  # 工程师对话会话ID
   231|    sender_type = Column(String(32))  # 'user', 'ai', 'agent'
   232|    event_summary_version = Column(String(64))  # 事件概要版本哈希
   233|    created_at = Column(DateTime, default=func.now())
   234|    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
   235|    
   236|    def to_dict(self):
   237|        return {
   238|            'id': self.id,
   239|            'message_id': self.message_id,
   240|            'event_id': self.event_id,
   241|            'user_id': self.user_id,
   242|            'message_from': self.message_from,
   243|            'round_id': self.round_id,
   244|            'message_content': self.message_content,
   245|            'message_type': self.message_type,
   246|            'message_category': self.message_category,
   247|            'chat_session_id': self.chat_session_id,
   248|            'sender_type': self.sender_type,
   249|            'event_summary_version': self.event_summary_version,
   250|            'created_at': self.created_at.isoformat() if self.created_at else None,
   251|            'updated_at': self.updated_at.isoformat() if self.updated_at else None
   252|        }
   253|
   254|class Summary(db.Model):
   255|    """事件总结表"""
   256|    __tablename__ = 'summaries'
   257|    
   258|    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
   259|    summary_id = db.Column(db.String(48), nullable=False, unique=True)
   260|    event_id = db.Column(db.String(48))
   261|    round_id = db.Column(db.Integer, default=0)
   262|    event_summary = db.Column(db.Text)
   263|    event_suggestion = db.Column(db.Text)
   264|    # root_cause = db.Column(db.Text)
   265|    # prevention = db.Column(db.Text)
   266|    created_at = db.Column(db.DateTime, default=datetime.utcnow)
   267|    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
   268|
   269|    def to_dict(self):
   270|        return {
   271|            'id': self.id,
   272|            'summary_id': self.summary_id,
   273|            'event_id': self.event_id,
   274|            'round_id': self.round_id,
   275|            'event_summary': self.event_summary,
   276|            'event_suggestion': self.event_suggestion,
   277|            # 'root_cause': self.root_cause,
   278|            # 'prevention': self.prevention,
   279|            'created_at': self.created_at.isoformat() if self.created_at else None,
   280|            'updated_at': self.updated_at.isoformat() if self.updated_at else None
   281|        }
   282|
   283|class LLMRecord(db.Model):
   284|    """大模型请求记录表"""
   285|    __tablename__ = "llm_records"
   286|
   287|    id = Column(Integer, primary_key=True, autoincrement=True)
   288|    request_id = db.Column(db.String(128), nullable=True)  # 请求ID，如OpenAI的id字段
   289|    model_name = db.Column(db.String(64), nullable=False)  # 使用的模型名称
   290|    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 请求创建时间
   291|    request_messages = db.Column(db.JSON, nullable=False)  # 请求的完整messages
   292|    response_content = db.Column(db.Text, nullable=True)  # 响应内容
   293|    response_full = db.Column(db.JSON, nullable=True)  # 完整响应
   294|    prompt_tokens = db.Column(db.Integer, nullable=True)  # 提示词token数
   295|    completion_tokens = db.Column(db.Integer, nullable=True)  # 完成词token数
   296|    total_tokens = db.Column(db.Integer, nullable=True)  # 总token数
   297|    cached_tokens = db.Column(db.Integer, nullable=True)  # 缓存token数
   298|    
   299|    def to_dict(self):
   300|        return {
   301|            'id': self.id,
   302|            'request_id': self.request_id,
   303|            'model_name': self.model_name,
   304|            'created_at': self.created_at.isoformat() if self.created_at else None,
   305|            'request_messages': self.request_messages,
   306|            'response_content': self.response_content,
   307|            'response_full': self.response_full,
   308|            'prompt_tokens': self.prompt_tokens,
   309|            'completion_tokens': self.completion_tokens,
   310|            'total_tokens': self.total_tokens,
   311|            'cached_tokens': self.cached_tokens
   312|        }
   313|
   314|
   315|class Prompt(db.Model):
   316|    """存储提示词和背景信息"""
   317|    __tablename__ = 'prompts'
   318|
   319|    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
   320|    name = db.Column(db.String(64), unique=True, nullable=False)
   321|    content = db.Column(db.Text, default='')
   322|    created_at = db.Column(db.DateTime, default=datetime.utcnow)
   323|    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
   324|
   325|    def to_dict(self):
   326|        return {
   327|            'id': self.id,
   328|            'name': self.name,
   329|            'content': self.content,
   330|            'created_at': self.created_at.isoformat() if self.created_at else None,
   331|            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
   332|        }
   333|
   334|
   335|class MCPServer(db.Model):
   336|    """MCP Server 配置表"""
   337|    __tablename__ = 'mcp_servers'
   338|    
   339|    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
   340|    server_key = db.Column(db.String(64), unique=True, nullable=False)
   341|    name = db.Column(db.String(128), nullable=False)
   342|    description = db.Column(db.Text)
   343|    transport_type = db.Column(db.String(32), default='sse') # stdio, sse, http
   344|    base_url = db.Column(db.String(256))
   345|    auth_token = db.Column(db.String(256)) # 可以加密存储
   346|    timeout = db.Column(db.Integer, default=30)
   347|    status = db.Column(db.String(32), default='disabled') # disabled, enabled, active, error
   348|    tools_count = db.Column(db.Integer, default=0)
   349|    last_check_at = db.Column(db.DateTime)
   350|    created_at = db.Column(db.DateTime, default=datetime.utcnow)
   351|    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
   352|
   353|    def to_dict(self):
   354|        return {
   355|            'id': self.id,
   356|            'server_key': self.server_key,
   357|            'name': self.name,
   358|            'description': self.description,
   359|            'transport_type': self.transport_type,
   360|            'base_url': self.base_url,
   361|            # auth_token 不返回前端
   362|            'timeout': self.timeout,
   363|            'status': self.status,
   364|            'tools_count': self.tools_count,
   365|            'last_check_at': self.last_check_at.isoformat() if self.last_check_at else None,
   366|            'created_at': self.created_at.isoformat() if self.created_at else None,
   367|            'updated_at': self.updated_at.isoformat() if self.updated_at else None
   368|        }
   369|
   370|class MCPTool(db.Model):
   371|    """MCP 工具缓存表"""
   372|    __tablename__ = 'mcp_tools'
   373|    
   374|    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
   375|    server_id = db.Column(db.Integer, db.ForeignKey('mcp_servers.id'))
   376|    name = db.Column(db.String(128), nullable=False)
   377|    description = db.Column(db.Text)
   378|    input_schema = db.Column(db.JSON) # JSON Schema
   379|    created_at = db.Column(db.DateTime, default=datetime.utcnow)
   380|    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
   381|
   382|    def to_dict(self):
   383|        return {
   384|            'id': self.id,
   385|            'server_id': self.server_id,
   386|            'name': self.name,
   387|            'description': self.description,
   388|            'input_schema': self.input_schema,
   389|            'updated_at': self.updated_at.isoformat() if self.updated_at else None
   390|        }
   391|
   392|class GlobalSetting(db.Model):
   393|    """全局设置表，用于存储系统级状态"""
   394|    __tablename__ = 'global_settings'
   395|
   396|    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
   397|    key = db.Column(db.String(64), unique=True, nullable=False)
   398|    value = db.Column(db.String(256), nullable=True)
   399|    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
   400|
   401|    def to_dict(self):
   402|        return {
   403|            'key': self.key,
   404|            'value': self.value,
   405|            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
   406|        }
   407|
   408|class LLMConfig(db.Model):
   409|    """大模型配置表"""
   410|    __tablename__ = 'llm_configs'
   411|
   412|    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
   413|    config_type = db.Column(db.String(32), unique=True, nullable=False) # 'reasoning' or 'summary'
   414|    api_type = db.Column(db.String(32), default='openai') # openai, azure
   415|    api_base = db.Column(db.String(256))
   416|    api_key = db.Column(db.Text)
   417|    model_name = db.Column(db.String(128))
   418|    api_version = db.Column(db.String(64))
   419|    temperature = db.Column(db.Float, default=0.7)
   420|    is_active = db.Column(db.Boolean, default=True)
   421|    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
   422|
   423|    def to_dict(self):
   424|        return {
   425|            'id': self.id,
   426|            'config_type': self.config_type,
   427|            'api_type': self.api_type,
   428|            'api_base': self.api_base,
   429|            'has_api_key': bool(self.api_key),
   430|            'model_name': self.model_name,
   431|            'api_version': self.api_version,
   432|            'temperature': self.temperature,
   433|            'is_active': self.is_active,
   434|            'updated_at': self.updated_at.isoformat() if self.updated_at else None
   435|        }
