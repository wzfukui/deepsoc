from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.models import db, LLMConfig, User
import logging
import traceback

llm_config_bp = Blueprint('llm_config', __name__)
logger = logging.getLogger(__name__)

# 获取配置
@llm_config_bp.route('/', methods=['GET'])
@jwt_required()
def get_configs():
    try:
        # Check admin role
        current_user = get_jwt_identity()
        user = User.query.filter_by(username=current_user).first()
        if not user or user.role != 'admin':
            return jsonify({'status': 'error', 'message': 'Permission denied'}), 403

        configs = LLMConfig.query.all()
        # Transform to list of dicts
        # Ensure we have both types even if empty in DB
        result = {
            'reasoning': None,
            'summary': None
        }
        
        for c in configs:
            if c.config_type in result:
                result[c.config_type] = c.to_dict()
                
        return jsonify({
            'status': 'success',
            'data': result
        })
    except Exception as e:
        logger.error(f"Error fetching LLM configs: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# 保存配置
@llm_config_bp.route('/', methods=['POST'])
@jwt_required()
def save_config():
    try:
        # Check admin role
        current_user = get_jwt_identity()
        user = User.query.filter_by(username=current_user).first()
        if not user or user.role != 'admin':
            return jsonify({'status': 'error', 'message': 'Permission denied'}), 403

        data = request.json
        config_type = data.get('config_type')
        if config_type not in ['reasoning', 'summary']:
            return jsonify({'status': 'error', 'message': 'Invalid config_type'}), 400
            
        config = LLMConfig.query.filter_by(config_type=config_type).first()
        if not config:
            config = LLMConfig(config_type=config_type)
            db.session.add(config)
            
        # Update fields
        config.api_type = data.get('api_type', 'openai')
        config.api_base = data.get('api_base')
        config.model_name = data.get('model_name')
        config.api_version = data.get('api_version')
        config.temperature = float(data.get('temperature', 0.7))
        config.is_active = data.get('is_active', True)
        
        # Only update key if provided (don't overwrite with empty if not intended)
        if data.get('api_key'):
            config.api_key = data.get('api_key')
            
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Configuration saved',
            'data': config.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving LLM config: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# 测试连接
@llm_config_bp.route('/test', methods=['POST'])
@jwt_required()
def test_connection():
    try:
        # Check admin role
        current_user = get_jwt_identity()
        user = User.query.filter_by(username=current_user).first()
        if not user or user.role != 'admin':
            return jsonify({'status': 'error', 'message': 'Permission denied'}), 403

        data = request.json
        # Create a temporary client using provided data
        from openai import OpenAI
        
        # Handle cases where API key is not provided in request (e.g. using saved one)
        api_key = data.get('api_key')
        if not api_key:
             # Try to fetch from DB if config_type is present
             config_type = data.get('config_type')
             if config_type:
                 config = LLMConfig.query.filter_by(config_type=config_type).first()
                 if config:
                     api_key = config.api_key
        
        if not api_key:
            return jsonify({'status': 'error', 'message': 'API Key is missing'}), 400

        client = OpenAI(
            api_key=api_key,
            base_url=data.get('api_base')
        )
        
        model = data.get('model_name')
        
        # Simple test call
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5
        )
        
        return jsonify({
            'status': 'success',
            'message': 'Connection successful',
            'response': response.choices[0].message.content
        })
        
    except Exception as e:
        logger.error(f"Test connection failed: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
