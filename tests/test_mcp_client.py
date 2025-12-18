import asyncio
import logging
import os
import json
from fastmcp import Client

# Configure logging to see what's happening
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_fastmcp_client():
    # 测试配置 (默认使用提供的USG防火墙配置)
    DEFAULT_BASE_URL = "https://mcp.51pwd.com/Firewall/USGFirewall"
    DEFAULT_TOKEN = "75cef760-a70d-412e-8481-fdc699e4c7d8"
    
    # 也可以从环境变量或命令行参数获取
    base_url = os.getenv("MCP_TEST_URL", f"{DEFAULT_BASE_URL}?token={DEFAULT_TOKEN}")
    
    print(f"\n--- Testing MCP Server with FastMCP: {base_url} ---")
    
    try:
        # FastMCP Client context manager handles connection and cleanup
        async with Client(base_url) as client:
            print("\n--- Connected! ---")
            
            print("\n--- Listing Tools ---")
            tools = await client.list_tools()
            if tools:
                print(f"Found {len(tools)} tools:")
                for tool in tools:
                    # FastMCP Tool object
                    print(f"  - {tool.name}: {tool.description}")
                    
                    # 检查 parameters 属性
                    # FastMCP 2.x 的 Tool 对象可能结构有所不同
                    # 在 mcp 库中，Tool 对象的 inputSchema 属性存储了参数定义
                    # 而 FastMCP 对此进行了封装，可能是 parameters, args_schema, 或者其他
                    
                    # 尝试打印对象的所有属性以进行调试
                    # print(f"    Tool Attributes: {dir(tool)}")
                    
                    if hasattr(tool, 'inputSchema'):
                        schema = tool.inputSchema
                        # print(f"    Schema (inputSchema): {json.dumps(schema, ensure_ascii=False)}")
                    elif hasattr(tool, 'parameters'):
                         # 之前的代码假设是 parameters 并且是 Pydantic 模型
                         # 如果是 dict，直接使用
                         if isinstance(tool.parameters, dict):
                             schema = tool.parameters
                         elif hasattr(tool.parameters, 'model_json_schema'):
                             schema = tool.parameters.model_json_schema()
                         else:
                             # print(f"    Parameters (unknown type): {type(tool.parameters)}")
                             schema = {}
                    else:
                        print("    No parameters/schema found")
                        schema = {}

            else:
                print("No tools found.")
                
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(test_fastmcp_client())
    except KeyboardInterrupt:
        pass
