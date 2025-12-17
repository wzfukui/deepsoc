import sys
import os
from flask import Flask
from app.models import db, LLMConfig
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def init_llm_config():
    with app.app_context():
        # Common settings
        api_base = os.getenv('LLM_BASE_URL')
        api_key = os.getenv('LLM_API_KEY')
        temp_val = os.getenv('LLM_TEMPERATURE', '0.6')
        try:
            temp = float(temp_val)
        except:
            temp = 0.6
        
        print(f"Initializing LLM Configs...")
        print(f"Base: {api_base}")
        print(f"Model: {os.getenv('LLM_MODEL')}")
        
        # 1. Reasoning Config
        reasoning = LLMConfig.query.filter_by(config_type='reasoning').first()
        if not reasoning:
            reasoning = LLMConfig(config_type='reasoning')
            db.session.add(reasoning)
        
        reasoning.api_type = 'openai'
        reasoning.api_base = api_base
        reasoning.api_key = api_key
        reasoning.model_name = os.getenv('LLM_MODEL', 'qwen-plus')
        reasoning.temperature = temp
        reasoning.is_active = True
        
        # 2. Summary Config
        summary = LLMConfig.query.filter_by(config_type='summary').first()
        if not summary:
            summary = LLMConfig(config_type='summary')
            db.session.add(summary)
            
        summary.api_type = 'openai'
        summary.api_base = api_base
        summary.api_key = api_key
        summary.model_name = os.getenv('LLM_MODEL_LONG_TEXT', 'qwen-long')
        summary.temperature = temp
        summary.is_active = True
        
        db.session.commit()
        print("LLM Configs initialized successfully.")

if __name__ == "__main__":
    init_llm_config()
