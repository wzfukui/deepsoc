import os
import json
import requests
import yaml
import logging
from dotenv import load_dotenv
from openai import OpenAI
from app.models.models import db, LLMRecord

# 加载环境变量
load_dotenv()

# 大模型配置
LLM_BASE_URL = os.getenv('LLM_BASE_URL', 'https://api.openai.com/v1')
LLM_API_KEY = os.getenv('LLM_API_KEY')
LLM_MODEL = os.getenv('LLM_MODEL', 'gpt-4o-mini')
LLM_MODEL_LONG_TEXT = os.getenv('LLM_MODEL_LONG_TEXT', 'qwen-long')
LLM_TEMPERATURE = float(os.getenv('LLM_TEMPERATURE', 0.6))

# 全局客户端实例
_client = None

def get_client():
    global _client
    if _client is None:
        if not LLM_API_KEY:
            raise ValueError("LLM_API_KEY环境变量未设置")
        _client = OpenAI(
            api_key=LLM_API_KEY,
            base_url=LLM_BASE_URL
        )
    return _client

def call_llm(system_prompt, user_prompt, history=None, temperature=None, long_text=False, 
             stream=False, json_mode=False, tools=None, tool_choice=None, **kwargs):
    """调用大模型API
    
    Args:
        system_prompt: 系统提示词
        user_prompt: 用户提示词
        history: 历史对话记录，格式为[{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
        temperature: 温度参数，控制随机性
        long_text: 是否使用长文本模型
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
    client = get_client()
    model = LLM_MODEL_LONG_TEXT if long_text else LLM_MODEL
    
    # 构建消息列表
    messages = [{"role": "system", "content": system_prompt}]
    
    # 添加历史对话
    if history:
        messages.extend(history)
    
    # 添加当前用户提示
    # 如果 user_prompt 为空字符串但 history 存在，OpenAI 可能报错，但这里我们假设调用方会控制
    if user_prompt:
        messages.append({"role": "user", "content": user_prompt})
    
    # 设置温度参数
    temp = temperature if temperature is not None else LLM_TEMPERATURE
    
    # 构建API参数
    api_params = {
        "model": model,
        "messages": messages,
        "temperature": temp,
        "stream": stream,
    }
    
    if tools:
        api_params["tools"] = tools
        if tool_choice:
            api_params["tool_choice"] = tool_choice
    
    if json_mode and not tools: # JSON mode usually not compatible with tools in some contexts or redundant
        api_params["response_format"] = {"type": "json_object"}
        
    # 合并其他参数
    api_params.update(kwargs)
    
    try:
        response = client.chat.completions.create(**api_params)
        
        if stream:
            if tools:
                 logging.warning("Stream mode is not fully supported with tools in this implementation yet.")
            return _handle_stream_response(response, model, messages, api_params)
        else:
            return _handle_normal_response(response, model, messages, api_params, tools_enabled=(tools is not None))
            
    except Exception as e:
        logging.error(f"调用LLM失败: {e}")
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
            model_name=response.model,
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
            return message # Return full message object for tool handling
        else:
            return content # Keep backward compatibility
            
    except Exception as e:
        logging.error(f"处理LLM响应失败: {e}")
        # 如果处理响应出错，尝试返回原始内容或抛出
        if hasattr(response, 'choices') and response.choices:
            return response.choices[0].message.content
        raise e

def _handle_stream_response(response, model, messages, api_params):
    """处理流式响应"""
    # 用于收集完整内容以便记录
    full_content = []
    full_reasoning = []
    request_id = None
    model_name = model # 默认使用请求的模型名，流式响应可能不包含model字段在每个chunk
    
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
            prompt_tokens=None, # 流式通常没有usage
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
        # 不抛出异常，以免影响主流程
        # 尝试 rollback
        try:
            db.session.rollback()
        except:
            pass

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
