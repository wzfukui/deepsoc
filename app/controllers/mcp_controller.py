from flask import Blueprint, request, jsonify
from app.models import db, MCPServer, MCPTool
from app.mcp import MCPManager
import uuid

mcp_bp = Blueprint('mcp', __name__)

@mcp_bp.route('/servers', methods=['GET'])
def list_servers():
    servers = MCPServer.query.all()
    return jsonify({
        'status': 'success',
        'data': [s.to_dict() for s in servers]
    })

@mcp_bp.route('/servers', methods=['POST'])
def create_server():
    data = request.json
    if not data or not data.get('name') or not data.get('base_url'):
        return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400
    
    # 检查 server_key 唯一性
    server_key = data.get('server_key')
    if not server_key:
        # 自动生成 key
        server_key = str(uuid.uuid4()).split('-')[0] # 简短一点
    
    if MCPServer.query.filter_by(server_key=server_key).first():
        return jsonify({'status': 'error', 'message': 'Server Key already exists'}), 400

    new_server = MCPServer(
        server_key=server_key,
        name=data.get('name'),
        description=data.get('description'),
        transport_type=data.get('transport_type', 'sse'),
        base_url=data.get('base_url'),
        auth_token=data.get('auth_token'),
        timeout=int(data.get('timeout', 30)),
        status='disabled'
    )
    
    try:
        db.session.add(new_server)
        db.session.commit()
        return jsonify({'status': 'success', 'data': new_server.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@mcp_bp.route('/servers/<int:server_id>', methods=['PUT'])
def update_server(server_id):
    server = MCPServer.query.get_or_404(server_id)
    data = request.json
    
    if 'name' in data: server.name = data['name']
    if 'description' in data: server.description = data['description']
    if 'base_url' in data: server.base_url = data['base_url']
    if 'transport_type' in data: server.transport_type = data['transport_type']
    if 'auth_token' in data: server.auth_token = data['auth_token']
    if 'timeout' in data: server.timeout = int(data['timeout'])
    if 'status' in data: server.status = data['status'] # Allow manual enable/disable
    
    try:
        db.session.commit()
        return jsonify({'status': 'success', 'data': server.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@mcp_bp.route('/servers/<int:server_id>', methods=['DELETE'])
def delete_server(server_id):
    server = MCPServer.query.get_or_404(server_id)
    try:
        # 删除关联的工具
        MCPTool.query.filter_by(server_id=server.id).delete()
        db.session.delete(server)
        db.session.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@mcp_bp.route('/servers/<int:server_id>/sync', methods=['POST'])
def sync_server(server_id):
    """测试连接并同步工具"""
    server = MCPServer.query.get_or_404(server_id)
    
    success = MCPManager.sync_server_tools_sync(server_id)
    
    if success:
        server = MCPServer.query.get(server_id) # Reload
        return jsonify({
            'status': 'success', 
            'message': f'Sync successful. Found {server.tools_count} tools.',
            'data': server.to_dict()
        })
    else:
        return jsonify({'status': 'error', 'message': 'Sync failed. Check logs for details.'}), 500

@mcp_bp.route('/tools', methods=['GET'])
def list_tools():
    """列出所有缓存的工具"""
    server_id = request.args.get('server_id')
    if server_id:
        tools = MCPTool.query.filter_by(server_id=server_id).all()
    else:
        tools = MCPTool.query.all()
        
    return jsonify({
        'status': 'success',
        'data': [t.to_dict() for t in tools]
    })
