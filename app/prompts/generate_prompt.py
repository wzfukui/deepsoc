#!/usr/bin/env python3

import os
import sys


def generate_prompt_for_captain():
    prompt_default = ""
    with open("prompts/role_soc_captain.md", "r") as f:
        prompt_default = f.read()

    prompt_background = ""
    with open("prompts/background_security.md", "r") as f:
        prompt_background = f.read()

    prompt = prompt_default.replace("{background_info}", prompt_background)

    return prompt


def generate_prompt_for_analyst():
    prompt_default = ""
    with open("prompts/role_soc_analyst.md", "r") as f:
        prompt_default = f.read()

    prompt_background = ""
    with open("prompts/background_security.md", "r") as f:
        prompt_background = f.read()

    prompt_playbooks = ""
    with open("prompts/background_soar_playbooks.md", "r") as f:
        prompt_playbooks = f.read()

    prompt = prompt_default.replace("{background_info}", prompt_background)
    prompt = prompt.replace("{playbook_list}", prompt_playbooks)

    return prompt



def generate_prompt_for_responder():
    prompt_default = ""
    with open("prompts/role_soc_responder.md", "r") as f:
        prompt_default = f.read()

    prompt_background = ""
    with open("prompts/background_security.md", "r") as f:
        prompt_background = f.read()

    playbook_list = ""
    with open("prompts/background_soar_playbooks.md", "r") as f:
        playbook_list = f.read()

    prompt = prompt_default.replace("{background_info}", prompt_background)
    prompt = prompt.replace("{playbook_list}", playbook_list)

    return prompt

def generate_prompt_for_operator():
    prompt_default = ""
    with open("prompts/role_soc_operator.md", "r") as f:
        prompt_default = f.read()

    background_info = ""
    with open("prompts/background_security.md", "r") as f:
        background_info = f.read()

    playbook_list = ""
    with open("prompts/background_soar_playbooks.md", "r") as f:
        playbook_list = f.read()

    prompt = prompt_default.replace("{background_info}", background_info)
    prompt = prompt.replace("{playbook_list}", playbook_list)

    return prompt

if __name__ == "__main__":
    generate_prompt_for_commander()
    generate_prompt_for_analyst()
    generate_prompt_for_responder()
    generate_prompt_for_operator()