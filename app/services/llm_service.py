import os
import json
import requests
import yaml
import logging
from dotenv import load_dotenv
from openai import OpenAI
from app.models.models import db, LLMRecord, LLMConfig

# 加载环境变量
load_dotenv()

# 大模型配置 (环境变量作为默认/回退)
LLM_BASE_URL = os.getenv('LLM_BASE_URL', 'https://api.openai.com/v1')
LLM_API_KEY = os.getenv('LLM_API_KEY')
LLM_MODEL = os.getenv('LLM_MODEL', 'gpt-4o-mini')
LLM_MODEL_LONG_TEXT = os.getenv('LLM_MODEL_LONG_TEXT', 'qwen-long')
LLM_TEMPERATURE = float(os.getenv('LLM_TEMPERATURE', 0.6))

# 全局客户端实例缓存 (仅用于环境变量配置的情况，或者可以扩展为按config_type缓存)
_env_client = None

def get_client_and_model(config_type='reasoning'):
    """
    获取LLM客户端和模型名称。
    优先从数据库读取配置，如果不存在或未激活，则回退到环境变量。
    
    Args:
        config_type: 'reasoning' 或 'summary'
    
    Returns:
        (client, model_name)
    """
    global _env_client
    
    # 尝试从数据库获取配置
    try:
        # 注意：这里假设在Flask应用上下文中调用。如果在非应用上下文（如独立脚本）可能需要处理
        config = LLMConfig.query.filter_by(config_type=config_type, is_active=True).first()
        
        if config and config.api_key:
            # 使用数据库配置创建客户端
            # TODO: 这里可以添加缓存逻辑，避免每次请求都创建客户端
            client = OpenAI(
                api_key=config.api_key,
                base_url=config.api_base if config.api_base else LLM_BASE_URL
            )
            model_name = config.model_name
            return client, model_name
            
    except Exception as e:
        # 数据库查询失败（可能是表未创建，或者不在上下文中）
        logging.warning(f"读取数据库LLM配置失败({config_type}): {e}，回退到环境变量")

    # 回退到环境变量
    if _env_client is None:
        if not LLM_API_KEY:
            raise ValueError("LLM_API_KEY环境变量未设置且无有效的数据库配置")
        _env_client = OpenAI(
            api_key=LLM_API_KEY,
            base_url=LLM_BASE_URL
        )
    
    # 根据类型返回默认模型名
    if config_type == 'summary':
        model_name = LLM_MODEL_LONG_TEXT
    else:
        model_name = LLM_MODEL
    
    return _env_client, model_name

def call_llm(system_prompt, user_prompt, history=None, temperature=None, long_text=False, 
             stream=False, json_mode=False, tools=None, tool_choice=None, **kwargs):
    """调用大模型API
    
    Args:
        system_prompt: 系统提示词
        user_prompt: 用户提示词
        history: 历史对话记录，格式为[{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
        temperature: 温度参数，控制随机性
        long_text: 是否使用长文本模型 (对应 'summary' 配置)
        stream: 是否使用流式输出
        json_mode: 是否强制JSON格式输出
        tools: OpenAI格式的工具定义列表
        tool_choice: 工具选择策略 (auto, required, or specific tool)
        **kwargs: 传递给OpenAI API的其他参数
        
    Returns:
        如果stream=False:
           - 如果 tools 为 None，返回文本内容 (str)
           - 如果 tools 不为 None，返回 OpenAI ChatCompletionMessage 对象 (包含 content 和 tool_calls)
        如果stream=True，返回生成器，生成每个chunk的内容 (不支持 tools)
    """
    # 确定配置类型
    config_type = 'summary' if long_text else 'reasoning'
    
    # 获取客户端和模型名
    client, model_name = get_client_and_model(config_type)
    
    # 如果调用方强制指定了 model 参数，则覆盖自动获取的
    if 'model' in kwargs:
        model_name = kwargs.pop('model')
    
    # 构建消息列表
    messages = [{"role": "system", "content": system_prompt}]
    
    # 添加历史对话
    if history:
        messages.extend(history)
    
    # 添加当前用户提示
    if user_prompt:
        messages.append({"role": "user", "content": user_prompt})
    
    # 设置温度参数
    # 尝试从数据库配置获取温度（如果数据库中有配置）
    db_temp = None
    try:
        config = LLMConfig.query.filter_by(config_type=config_type, is_active=True).first()
        if config:
            db_temp = config.temperature
    except:
        pass
        
    # 优先级: 参数传入 > 数据库配置 > 环境变量默认
    if temperature is not None:
        temp = temperature
    elif db_temp is not None:
        temp = db_temp
    else:
        temp = LLM_TEMPERATURE
    
    # 构建API参数
    api_params = {
        "model": model_name,
        "messages": messages,
        "temperature": temp,
        "stream": stream,
    }
    
    if tools:
        api_params["tools"] = tools
        if tool_choice:
            api_params["tool_choice"] = tool_choice
    
    if json_mode and not tools: 
        api_params["response_format"] = {"type": "json_object"}
        
    # 合并其他参数
    api_params.update(kwargs)
    
    try:
        response = client.chat.completions.create(**api_params)
        
        if stream:
            if tools:
                 logging.warning("Stream mode is not fully supported with tools in this implementation yet.")
            return _handle_stream_response(response, model_name, messages, api_params)
        else:
            return _handle_normal_response(response, model_name, messages, api_params, tools_enabled=(tools is not None))
            
    except Exception as e:
        logging.error(f"调用LLM失败(config={config_type}, model={model_name}): {e}")
        raise e

def _handle_normal_response(response, model, messages, api_params, tools_enabled=False):
    """处理普通（非流式）响应"""
    try:
        choice = response.choices[0]
        message = choice.message
        content = message.content
        
        # 尝试获取 reasoning_content (DeepSeek R1等)
        reasoning_content = getattr(message, 'reasoning_content', None)
        
        # 准备记录的数据
        usage = response.usage
        prompt_tokens = usage.prompt_tokens if usage else None
        completion_tokens = usage.completion_tokens if usage else None
        total_tokens = usage.total_tokens if usage else None
        cached_tokens = None
        if hasattr(usage, 'prompt_tokens_details') and usage.prompt_tokens_details:
             cached_tokens = getattr(usage.prompt_tokens_details, 'cached_tokens', None)
        
        # 记录到数据库
        _save_llm_record(
            request_id=response.id,
            model_name=model, # 使用实际调用的模型名
            messages=messages,
            response_content=content,
            response_full=response.model_dump(),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cached_tokens=cached_tokens,
            reasoning_content=reasoning_content
        )
        
        if tools_enabled:
            return message 
        else:
            return content 
            
    except Exception as e:
        logging.error(f"处理LLM响应失败: {e}")
        if hasattr(response, 'choices') and response.choices:
            return response.choices[0].message.content
        raise e

def _handle_stream_response(response, model, messages, api_params):
    """处理流式响应"""
    full_content = []
    full_reasoning = []
    request_id = None
    model_name = model 
    
    try:
        for chunk in response:
            if not request_id and chunk.id:
                request_id = chunk.id
            if chunk.model:
                model_name = chunk.model
                
            if chunk.choices:
                delta = chunk.choices[0].delta
                
                # 处理内容
                if delta.content:
                    content_piece = delta.content
                    full_content.append(content_piece)
                    yield content_piece
                
                # 处理推理内容
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                    reasoning_piece = delta.reasoning_content
                    full_reasoning.append(reasoning_piece)
                    
        # 流结束后记录
        content_str = "".join(full_content)
        reasoning_str = "".join(full_reasoning) if full_reasoning else None
        
        response_full = {
            "streamed": True,
            "content": content_str,
            "reasoning_content": reasoning_str
        }
        
        _save_llm_record(
            request_id=request_id,
            model_name=model_name,
            messages=messages,
            response_content=content_str,
            response_full=response_full,
            prompt_tokens=None, 
            completion_tokens=None,
            total_tokens=None,
            cached_tokens=None,
            reasoning_content=reasoning_str
        )
        
    except Exception as e:
        logging.error(f"流式处理失败: {e}")
        raise e

def _save_llm_record(request_id, model_name, messages, response_content, response_full, 
                     prompt_tokens, completion_tokens, total_tokens, cached_tokens, reasoning_content=None):
    """保存调用记录"""
    try:
        # 如果有 reasoning_content，添加到 response_full 中
        if reasoning_content:
            if isinstance(response_full, dict):
                response_full['reasoning_content'] = reasoning_content
            
        llm_record = LLMRecord(
            request_id=request_id,
            model_name=model_name,
            request_messages=messages,
            response_content=response_content,
            response_full=response_full,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cached_tokens=cached_tokens
        )
        
        # 使用当前上下文的 session
        db.session.add(llm_record)
        db.session.commit()
    except Exception as e:
        logging.error(f"记录LLM请求失败: {e}")
        try:
            db.session.rollback()
        except:
            pass

def parse_yaml_response(response_text):
    """解析YAML格式的大模型响应"""
    try:
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
            
        return yaml.safe_load(yaml_content)
    except Exception as e:
        print(f"YAML解析错误: {e}")
        print(f"原始响应: {response_text}")
        return None
