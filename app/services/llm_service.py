import os
import json
import yaml
from dotenv import load_dotenv
from openai import OpenAI, APIError
from app.models.models import db, LLMRecord

# 加载环境变量
load_dotenv()

# 大模型配置
LLM_BASE_URL = os.getenv('LLM_BASE_URL', 'https://api.openai.com/v1')
LLM_API_KEY = os.getenv('LLM_API_KEY')
LLM_MODEL = os.getenv('LLM_MODEL', 'gpt-4o-mini')
LLM_MODEL_LONG_TEXT = os.getenv('LLM_MODEL_LONG_TEXT', 'qwen-long')
LLM_TEMPERATURE = float(os.getenv('LLM_TEMPERATURE', 0.6))

# 初始化 OpenAI 客户端
client = None
if LLM_API_KEY:
    try:
        client = OpenAI(
            api_key=LLM_API_KEY,
            base_url=LLM_BASE_URL
        )
    except Exception as e:
        print(f"Warning: Failed to initialize OpenAI client: {e}")

def call_llm(system_prompt, user_prompt, history=None, temperature=None, long_text=False):
    """调用大模型API
    
    Args:
        system_prompt: 系统提示词
        user_prompt: 用户提示词
        history: 历史对话记录，格式为[{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
        temperature: 温度参数，控制随机性
        long_text: 是否使用长文本模型
        
    Returns:
        大模型返回的文本
    """
    if not client:
        raise ValueError("OpenAI Client未初始化，请检查LLM_API_KEY")
        
    model = LLM_MODEL_LONG_TEXT if long_text else LLM_MODEL
    
    # 构建消息列表
    messages = [{"role": "system", "content": system_prompt}]
    
    # 添加历史对话
    if history:
        messages.extend(history)
    
    # 添加当前用户提示
    messages.append({"role": "user", "content": user_prompt})
    
    # 设置温度参数
    temp = temperature if temperature is not None else LLM_TEMPERATURE
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temp
        )
        
        # 提取响应内容
        response_content = response.choices[0].message.content
        
        # 记录请求和响应
        try:
            # 提取usage信息
            usage = response.usage
            prompt_tokens = usage.prompt_tokens
            completion_tokens = usage.completion_tokens
            total_tokens = usage.total_tokens
            
            # 提取缓存token信息 (OpenAI SDK specific structure)
            cached_tokens = None
            if hasattr(usage, 'prompt_tokens_details') and usage.prompt_tokens_details:
                cached_tokens = getattr(usage.prompt_tokens_details, 'cached_tokens', None)
            
            # 创建记录
            llm_record = LLMRecord(
                request_id=response.id,
                model_name=response.model,
                request_messages=messages,
                response_content=response_content,
                response_full=response.model_dump(),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cached_tokens=cached_tokens
            )
            
            # 保存到数据库
            db.session.add(llm_record)
            db.session.commit()
        except Exception as e:
            print(f"记录LLM请求失败: {e}")
            # 记录失败不影响主流程
            
        return response_content

    except APIError as e:
        raise Exception(f"API请求失败: {e}")

def call_llm_structured(system_prompt, user_prompt, response_format, history=None, temperature=None, long_text=False):
    """调用大模型API并返回结构化数据
    
    Args:
        response_format: Pydantic模型类 或 JSON Schema dict
    """
    if not client:
        raise ValueError("OpenAI Client未初始化，请检查LLM_API_KEY")

    model = LLM_MODEL_LONG_TEXT if long_text else LLM_MODEL
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_prompt})
    temp = temperature if temperature is not None else LLM_TEMPERATURE

    try:
        # Check if response_format is a Pydantic model (class)
        if isinstance(response_format, type):
             completion = client.beta.chat.completions.parse(
                model=model,
                messages=messages,
                temperature=temp,
                response_format=response_format,
            )
             parsed_obj = completion.choices[0].message.parsed
             response_content = completion.choices[0].message.content # Raw content
             response_full = completion.model_dump()
        else:
            # Fallback for dict/JSON schema
            completion = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temp,
                response_format=response_format
            )
            response_content = completion.choices[0].message.content
            parsed_obj = json.loads(response_content)
            response_full = completion.model_dump()

        # Logging logic (duplicated for now, can be refactored)
        try:
            usage = completion.usage
            llm_record = LLMRecord(
                request_id=completion.id,
                model_name=completion.model,
                request_messages=messages,
                response_content=response_content,
                response_full=response_full,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens
            )
            db.session.add(llm_record)
            db.session.commit()
        except Exception as e:
            print(f"记录LLM请求失败: {e}")

        return parsed_obj

    except Exception as e:
         raise Exception(f"Structured API request failed: {e}")

def parse_yaml_response(response_text):
    """解析YAML格式的大模型响应
    
    Args:
        response_text: 大模型返回的YAML文本
        
    Returns:
        解析后的Python对象
    """
    try:
        # 尝试提取YAML部分
        if '```yaml' in response_text:
            yaml_parts = response_text.split('```yaml')
            if len(yaml_parts) > 1:
                yaml_content = yaml_parts[1].split('```')[0].strip()
            else:
                yaml_content = response_text
        elif '```' in response_text:
            yaml_parts = response_text.split('```')
            if len(yaml_parts) > 1:
                yaml_content = yaml_parts[1].strip()
            else:
                yaml_content = response_text
        else:
            yaml_content = response_text
            
        # 解析YAML
        return yaml.safe_load(yaml_content)
    except Exception as e:
        print(f"YAML解析错误: {e}")
        print(f"原始响应: {response_text}")
        return None
