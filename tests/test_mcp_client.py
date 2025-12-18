"""
MCP Client 测试脚本

功能说明：
1. 测试与 MCP 服务器的连接
2. 列出服务器上的所有工具
3. 可选：调用工具进行测试

使用方法：
    python tests/test_mcp_client.py                    # 默认只列出工具
    python tests/test_mcp_client.py --call-tool        # 列出工具并调用测试

注意：
- 某些 MCP 服务器 (Streamable HTTP 模式) 不支持 DELETE 方法关闭会话
- 这会导致 405 错误，但这是良性的，不影响功能
- Cherry Studio 等工具也会遇到同样的问题，只是它们隐藏了这个错误
"""

import asyncio
import logging
import os
import sys
import json
from fastmcp import Client

# Configure logging - 减少 httpx 的冗余输出
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 降低 httpx 的日志级别，避免显示每个 HTTP 请求（包括 405 错误）
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
# 降低 mcp 相关库的日志级别
logging.getLogger("mcp").setLevel(logging.WARNING)
logging.getLogger("fastmcp").setLevel(logging.WARNING)


async def safe_mcp_client_call(url, operation_fn):
    """
    安全地执行 MCP 客户端操作，优雅处理关闭时的 405 错误
    
    Args:
        url: MCP 服务器 URL
        operation_fn: 异步函数，接收 client 参数，执行实际操作
    
    Returns:
        operation_fn 的返回值
    """
    client = Client(url)
    try:
        await client.__aenter__()
        return await operation_fn(client)
    finally:
        try:
            await client.__aexit__(None, None, None)
        except Exception as e:
            # 某些 MCP 服务器不支持 DELETE 方法关闭会话，这是良性错误
            if "405" in str(e):
                logger.debug(f"Session cleanup returned 405 (benign): {e}")
            else:
                logger.warning(f"Error closing MCP session: {e}")


async def list_tools(client):
    """列出所有工具"""
    tools = await client.list_tools()
    return tools


async def call_tool(client, tool_name, arguments):
    """
    调用工具
    
    注意：FastMCP Client.call_tool() 的签名是：
        call_tool(name: str, arguments: dict | None = None, ...)
    参数应该作为 dict 传入，而不是展开为 **kwargs
    """
    result = await client.call_tool(tool_name, arguments)
    return result


async def test_fastmcp_client(call_test_tool=False):
    # 测试配置 (默认使用提供的USG防火墙配置)
    DEFAULT_BASE_URL = "https://mcp.51pwd.com/Firewall/USGFirewall"
    DEFAULT_TOKEN = "75cef760-a70d-412e-8481-fdc699e4c7d8"
    
    # 也可以从环境变量或命令行参数获取
    base_url = os.getenv("MCP_TEST_URL", f"{DEFAULT_BASE_URL}?token={DEFAULT_TOKEN}")
    
    print(f"\n--- Testing MCP Server with FastMCP: {base_url} ---")
    
    try:
        # 1. 列出工具
        print("\n--- Listing Tools ---")
        tools = await safe_mcp_client_call(base_url, list_tools)
        
        if tools:
            print(f"\n✅ 连接成功！找到 {len(tools)} 个工具:")
            for tool in tools:
                print(f"  - {tool.name}: {tool.description}")
                
                # 获取参数 schema
                if hasattr(tool, 'inputSchema') and tool.inputSchema:
                    schema = tool.inputSchema
                    properties = schema.get('properties', {})
                    required = schema.get('required', [])
                    if properties:
                        print(f"    参数:")
                        for param_name, param_info in properties.items():
                            required_mark = " (必填)" if param_name in required else ""
                            param_type = param_info.get('type', 'unknown')
                            param_desc = param_info.get('description', '')
                            print(f"      - {param_name}: {param_type}{required_mark} - {param_desc}")
        else:
            print("❌ 未找到任何工具")
            return
        
        # 2. 可选：调用工具测试
        if call_test_tool and tools:
            print("\n--- Testing Tool Call ---")
            # 选择 unblock_ip_address 工具进行测试（解封操作比较安全）
            test_tool = None
            for tool in tools:
                if tool.name == 'unblock_ip_address':
                    test_tool = tool
                    break
            
            if test_tool:
                test_ip = "8.8.8.8"  # 使用一个测试 IP
                print(f"\n调用工具: {test_tool.name}")
                print(f"参数: ip_address={test_ip}")
                
                async def call_test(client):
                    return await call_tool(client, test_tool.name, {"ip_address": test_ip})
                
                result = await safe_mcp_client_call(base_url, call_test)
                
                print(f"\n✅ 工具调用成功!")
                print(f"结果:")
                # FastMCP 返回 CallToolResult 对象，包含 content 列表
                if hasattr(result, 'content'):
                    for item in result.content:
                        if hasattr(item, 'text'):
                            # 尝试格式化 JSON 输出
                            try:
                                parsed = json.loads(item.text)
                                print(f"  {json.dumps(parsed, ensure_ascii=False, indent=2)}")
                            except json.JSONDecodeError:
                                print(f"  {item.text}")
                        else:
                            print(f"  {item}")
                elif isinstance(result, list):
                    for item in result:
                        if hasattr(item, 'text'):
                            print(f"  {item.text}")
                        else:
                            print(f"  {item}")
                else:
                    print(f"  {result}")
            else:
                print("⚠️ 未找到 unblock_ip_address 工具，跳过调用测试")
                
        print("\n--- 测试完成 ---")
                
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 检查是否要调用工具测试
    call_test = "--call-tool" in sys.argv or "-c" in sys.argv
    
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        sys.exit(0)
    
    try:
        asyncio.run(test_fastmcp_client(call_test_tool=call_test))
    except KeyboardInterrupt:
        pass
