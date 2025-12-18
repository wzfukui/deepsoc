import asyncio
import logging
import os
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
                    if tool.parameters:
                        # tool.parameters is a pydantic model class
                        schema = tool.parameters.model_json_schema()
                        # print(f"    Schema: {schema}") 
            else:
                print("No tools found.")
                
            # Example call (commented out)
            # print("\n--- Calling Tool (Example) ---")
            # result = await client.call_tool("tool_name", arg="value")
            # print(f"Result: {result}")
            
    except Exception as e:
        logger.error(f"Test failed: {e}")
        # import traceback
        # traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(test_fastmcp_client())
    except KeyboardInterrupt:
        pass
