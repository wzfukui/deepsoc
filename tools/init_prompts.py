#!/usr/bin/env python3
"""Import markdown prompts into the database.

Usage:
    python tools/init_prompts.py
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask
from app.models.models import db, Prompt

load_dotenv(override=True)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///deepsoc.db')

db.init_app(app)

PROMPT_DIR = Path(__file__).resolve().parent.parent / 'app' / 'prompts'
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
NAME_MAP = {
    '_captain': 'role_soc_captain',
    '_manager': 'role_soc_manager',
    '_operator': 'role_soc_operator',
    '_expert': 'role_soc_expert'
}


def load_file_to_db(name: str, path: Path):
    if not path.exists():
        return
    content = path.read_text(encoding='utf-8')
    with app.app_context():
        prompt = Prompt.query.filter_by(name=name).first()
        if not prompt:
            prompt = Prompt(name=name)
            db.session.add(prompt)
        prompt.content = content
        db.session.commit()


def main():
    for role, filename in ROLE_FILES.items():
        load_file_to_db(NAME_MAP[role], PROMPT_DIR / filename)
    for name, filename in BACKGROUND_FILES.items():
        load_file_to_db(name, PROMPT_DIR / filename)
    print('Prompts imported.')


if __name__ == '__main__':
    main()
