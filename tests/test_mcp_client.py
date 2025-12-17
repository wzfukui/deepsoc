import asyncio
import json
import os
import sys
import logging
import requests
import sseclient
from urllib.parse import urljoin

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestMCPClient:
    def __init__(self, base_url, auth_token=None):
        self.base_url = base_url
        self.auth_token = auth_token
        self.post_endpoint = None
        self.is_connected = False

    def connect(self):
        """连接到 MCP Server (SSE)"""
        logger.info(f"Connecting to MCP Server at {self.base_url}...")
        headers = {'Accept': 'text/event-stream'}
        if self.auth_token:
            headers['Authorization'] = f"Bearer {self.auth_token}"
        
        try:
            response = requests.get(self.base_url, stream=True, headers=headers, timeout=10)
            client = sseclient.SSEClient(response)
            
            for event in client.events():
                if event.event == 'endpoint':
                    self.post_endpoint = urljoin(self.base_url, event.data)
                    self.is_connected = True
                    logger.info(f"Connected! POST Endpoint: {self.post_endpoint}")
                    return True
                else:
                    logger.debug(f"Received event: {event.event}")
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
        return False

    def list_tools(self):
        """列出工具"""
        if not self.is_connected:
            if not self.connect():
                return None

        payload = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 1
        }
        return self._send_request(payload)

    def call_tool(self, tool_name, arguments):
        """调用工具"""
        if not self.is_connected:
            if not self.connect():
                return None

        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            },
            "id": 2
        }
        return self._send_request(payload)

    def _send_request(self, payload):
        headers = {'Content-Type': 'application/json'}
        if self.auth_token:
            headers['Authorization'] = f"Bearer {self.auth_token}"
            
        try:
            response = requests.post(self.post_endpoint, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            if 'error' in data:
                logger.error(f"JSON-RPC Error: {data['error']}")
                return None
            return data.get('result')
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return None

def main():
    # 测试配置 (默认使用提供的USG防火墙配置)
    DEFAULT_BASE_URL = "https://mcp.51pwd.com/Firewall/USGFirewall"
    DEFAULT_TOKEN = "75cef760-a70d-412e-8481-fdc699e4c7d8"
    
    # 也可以从环境变量或命令行参数获取
    base_url = os.getenv("MCP_TEST_URL", f"{DEFAULT_BASE_URL}?token={DEFAULT_TOKEN}")
    
    # 提取 token 如果在 url 中
    token = None
    if "?token=" in base_url:
        base_url_part, token_part = base_url.split("?token=")
        base_url = base_url  # Keep full URL for SSE usually, or split if needed by library. 
        # requests handles params in url fine. 
        # But for auth header logic above:
        token = token_part
    
    client = TestMCPClient(base_url)
    
    print(f"\n--- Testing MCP Server: {base_url} ---")
    
    # 1. Connect
    if not client.connect():
        sys.exit(1)
        
    # 2. List Tools
    print("\n--- Listing Tools ---")
    tools_result = client.list_tools()
    if tools_result:
        tools = tools_result.get('tools', [])
        print(f"Found {len(tools)} tools:")
        for t in tools:
            print(f"  - {t['name']}: {t.get('description', 'No description')}")
            print(f"    Schema: {json.dumps(t.get('inputSchema'), ensure_ascii=False)}")
    else:
        print("Failed to list tools.")
        
    # 3. Call Tool (Example)
    # You can customize this part to call a specific tool if you know the name
    # For now we just list them. To test call, uncomment below and set tool name.
    
    # tool_name = "block_ip" 
    # args = {"ip": "1.2.3.4"}
    # print(f"\n--- Calling Tool: {tool_name} ---")
    # result = client.call_tool(tool_name, args)
    # print(f"Result: {json.dumps(result, ensure_ascii=False, indent=2)}")

if __name__ == "__main__":
    main()
