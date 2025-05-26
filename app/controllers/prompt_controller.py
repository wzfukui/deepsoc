import logging
from pathlib import Path
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

prompt_bp = Blueprint('prompt', __name__)
logger = logging.getLogger(__name__)

PROMPT_DIR = Path(__file__).parent.parent / 'prompts'
ROLE_FILES = {
    '_captain': 'role_soc_captain.md',
    '_manager': 'role_soc_manager.md',
    '_operator': 'role_soc_operator.md',
    '_expert': 'role_soc_expert.md'
}

BACKGROUND_FILES = {
    'background_security': 'background_security.md',
    'background_soar_playbooks': 'background_soar_playbooks.md',
    'mcp_tools': 'mcp_tools.md'
}


def _load_prompt(role: str) -> str:
    file_path = PROMPT_DIR / ROLE_FILES[role]
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ''


def _save_prompt(role: str, content: str) -> None:
    file_path = PROMPT_DIR / ROLE_FILES[role]
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)


def _load_background(name: str) -> str:
    file_path = PROMPT_DIR / BACKGROUND_FILES[name]
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ''


def _save_background(name: str, content: str) -> None:
    file_path = PROMPT_DIR / BACKGROUND_FILES[name]
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)


@prompt_bp.route('/list', methods=['GET'])
@jwt_required()
def list_prompts():
    """Return prompts for all supported roles."""
    prompts = {role: _load_prompt(role) for role in ROLE_FILES}
    return jsonify({'status': 'success', 'data': prompts})


@prompt_bp.route('/<role>', methods=['GET', 'PUT'])
@jwt_required()
def handle_prompt(role):
    """Get or update prompt for a specific role."""
    if role not in ROLE_FILES:
        return jsonify({'status': 'error', 'message': '未知角色'}), 400

    if request.method == 'GET':
        return jsonify({'status': 'success', 'data': _load_prompt(role)})

    data = request.get_json() or {}
    content = data.get('prompt', '')
    try:
        _save_prompt(role, content)
        return jsonify({'status': 'success', 'message': '保存成功'})
    except Exception as e:
        logger.error(f'保存提示词失败: {e}')
        return jsonify({'status': 'error', 'message': '保存失败'}), 500


@prompt_bp.route('/background/<name>', methods=['GET', 'PUT'])
@jwt_required()
def handle_background(name):
    """Get or update background files."""
    if name not in BACKGROUND_FILES:
        return jsonify({'status': 'error', 'message': '未知文件'}), 400

    if request.method == 'GET':
        return jsonify({'status': 'success', 'data': _load_background(name)})

    data = request.get_json() or {}
    content = data.get('content', '')
    try:
        _save_background(name, content)
        return jsonify({'status': 'success', 'message': '保存成功'})
    except Exception as e:
        logger.error(f'保存背景文件失败: {e}')
        return jsonify({'status': 'error', 'message': '保存失败'}), 500
