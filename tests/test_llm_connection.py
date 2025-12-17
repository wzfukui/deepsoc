import sys
import os
import logging
from flask import current_app

# 添加项目根目录到 Python 路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app
from app.services.llm_service import call_llm

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_llm_connection():
    """测试LLM服务连通性"""
    print("\n" + "="*50)
    print("🚀 开始测试 LLM 服务连通性")
    print("="*50)

    try:
        # 1. 测试普通调用
        print("\n[1/3] 测试普通调用 (Normal Call)...")
        response = call_llm(
            system_prompt="你是一个有用的助手。",
            user_prompt="你好，请回复'Pong'。",
            temperature=0.1
        )
        print(f"✅ 普通调用成功！响应内容: {response}")

        # 2. 测试流式调用
        print("\n[2/3] 测试流式调用 (Stream Call)...")
        print("⏳ 正在接收流式响应: ", end="", flush=True)
        stream_response = call_llm(
            system_prompt="你是一个有用的助手。",
            user_prompt="请数到3。",
            stream=True,
            temperature=0.1
        )
        
        full_content = ""
        for chunk in stream_response:
            print(chunk, end="", flush=True)
            full_content += chunk
        print("\n✅ 流式调用成功！")

        # 3. 测试 JSON 模式 (如果模型支持)
        print("\n[3/3] 测试 JSON 模式 (JSON Mode)...")
        try:
            # 注意：使用 JSON mode 时，通常需要在 prompt 中明确提到 JSON
            json_response = call_llm(
                system_prompt="你是一个输出 JSON 的助手。",
                user_prompt="请生成一个包含 key='status' 和 value='ok' 的 JSON。",
                json_mode=True,
                temperature=0.1
            )
            print(f"✅ JSON 模式调用成功！响应内容: {json_response}")
        except Exception as e:
            print(f"⚠️ JSON 模式调用失败 (可能是模型不支持): {e}")

        print("\n" + "="*50)
        print("🎉 所有测试通过！LLM 服务工作正常。")
        print("="*50)

    except Exception as e:
        print("\n" + "="*50)
        print(f"❌ 测试失败: {e}")
        print("请检查 .env 文件配置或网络连接。")
        print("="*50)
        # 打印详细堆栈以便调试
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    # 使用应用上下文运行测试，确保数据库连接可用
    with app.app_context():
        test_llm_connection()
