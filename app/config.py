import os
from dotenv import load_dotenv
from types import SimpleNamespace

# 加载环境变量
load_dotenv()

# 创建配置对象
config = SimpleNamespace()

# SOAR配置
config.SOAR_API_URL = os.getenv('SOAR_API_URL', 'https://example.com')
config.SOAR_API_TOKEN = os.getenv('SOAR_API_TOKEN', '')
config.SOAR_API_TIMEOUT = int(os.getenv('SOAR_API_TIMEOUT', 30))
config.SOAR_RETRY_COUNT = int(os.getenv('SOAR_RETRY_COUNT', 3))
config.SOAR_RETRY_DELAY = int(os.getenv('SOAR_RETRY_DELAY', 5))

# LLM配置
config.LLM_BASE_URL = os.getenv('LLM_BASE_URL', 'https://api.openai.com/v1')
config.LLM_API_KEY = os.getenv('LLM_API_KEY', '')
config.LLM_MODEL = os.getenv('LLM_MODEL', 'gpt-4o-mini')
config.LLM_MODEL_LONG_TEXT = os.getenv('LLM_MODEL_LONG_TEXT', 'qwen-long')
config.LLM_TEMPERATURE = float(os.getenv('LLM_TEMPERATURE', 0.6))

# 事件处理配置
config.EVENT_MAX_ROUND = int(os.getenv('EVENT_MAX_ROUND', 3))

# 其他配置
config.DEBUG = os.getenv('DEBUG', 'False').lower() == 'true' 