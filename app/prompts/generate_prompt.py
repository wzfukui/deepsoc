#!/usr/bin/env python3
"""Utility to build prompts for different roles."""
from pathlib import Path

PROMPT_DIR = Path(__file__).parent
ROLE_FILES = {
    '_captain': 'role_soc_captain.md',
    '_manager': 'role_soc_manager.md',
    '_operator': 'role_soc_operator.md',
    '_expert': 'role_soc_expert.md'
}

BACKGROUND_FILE = PROMPT_DIR / 'background_security.md'
PLAYBOOK_FILE = PROMPT_DIR / 'background_soar_playbooks.md'


def generate_prompt(role: str) -> str:
    """Generate prompt text for the given role."""
    role_file = PROMPT_DIR / ROLE_FILES.get(role, '')
    if not role_file.exists():
        return ''
    background_info = BACKGROUND_FILE.read_text(encoding='utf-8') if BACKGROUND_FILE.exists() else ''
    playbook_list = PLAYBOOK_FILE.read_text(encoding='utf-8') if PLAYBOOK_FILE.exists() else ''
    prompt = role_file.read_text(encoding='utf-8')
    prompt = prompt.replace('{background_info}', background_info)
    prompt = prompt.replace('{playbook_list}', playbook_list)
    return prompt


def main():
    for role in ROLE_FILES:
        text = generate_prompt(role)
        print(f"==== {role} ====")
        print(text[:200] + ('...' if len(text) > 200 else ''))


if __name__ == '__main__':
    main()
