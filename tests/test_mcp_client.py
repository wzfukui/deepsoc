import json
import logging
import os
import sys
import requests
from urllib.parse import urljoin, urlparse, urlunparse, parse_qs, urlencode

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestMCPClient:
    def __init__(self, base_url, auth_token=None):
        self.base_url = base_url
        self.auth_token = auth_token
        self.post_endpoint = None
        self.is_connected = False

    def _parse_sse_line(self, line):
        """Helper to parse a single SSE line"""
        if not line:
            return None, None
        
        # Handle bytes vs string
        if isinstance(line, bytes):
            line = line.decode('utf-8', errors='replace')
            
        parts = line.split(':', 1)
        if len(parts) == 2:
            field = parts[0].strip()
            value = parts[1].strip()
            return field, value
        return None, None

    def connect(self):
        """连接到 MCP Server (SSE)"""
        logger.info(f"Connecting to MCP Server at {self.base_url}...")
        headers = {'Accept': 'text/event-stream'}
        if self.auth_token:
            headers['Authorization'] = f"Bearer {self.auth_token}"
        
        try:
            response = requests.get(self.base_url, stream=True, headers=headers, timeout=10)
            
            # Handle case where server returns JSON directly (not standard SSE handshake)
            content_type = response.headers.get('Content-Type', '').lower()
            if 'application/json' in content_type:
                logger.warning(f"Connect returned JSON, not SSE. Falling back to using base_url as endpoint.")
                self.post_endpoint = self.base_url
                self.is_connected = True
                return True

            # Manual SSE Parsing
            current_event = {}
            for line in response.iter_lines():
                if not line:
                    # Empty line -> End of event
                    if current_event:
                        if current_event.get('event') == 'endpoint':
                            # Found endpoint event
                            endpoint_url = current_event.get('data')
                            
                            # Resolve URL logic
                            full_url = urljoin(self.base_url, endpoint_url)
                            base_parsed = urlparse(self.base_url)
                            base_qs = parse_qs(base_parsed.query)
                            new_parsed = urlparse(full_url)
                            new_qs = parse_qs(new_parsed.query)
                            final_qs = new_qs.copy()
                            for k, v in base_qs.items():
                                if k not in final_qs:
                                    final_qs[k] = v
                            final_query = urlencode(final_qs, doseq=True)
                            self.post_endpoint = urlunparse(new_parsed._replace(query=final_query))

                            self.is_connected = True
                            logger.info(f"Connected! POST Endpoint: {self.post_endpoint}")
                            return True
                        current_event = {}
                    continue

                field, value = self._parse_sse_line(line)
                if field:
                    if field == 'data':
                        if 'data' in current_event:
                            current_event['data'] += "\n" + value
                        else:
                            current_event['data'] = value
                    else:
                        current_event[field] = value
            
            logger.warning("SSE stream ended without 'endpoint' event.")
            return False

        except Exception as e:
            logger.error(f"Connection failed: {e}")
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
            response = requests.post(self.post_endpoint, json=payload, headers=headers, timeout=30, stream=True)
            
            # Check for SSE response
            content_type = response.headers.get('Content-Type', '').lower()
            if 'text/event-stream' in content_type:
                logger.info(f"Response is SSE. Content-Type: {content_type}")
                
                current_event = {}
                for line in response.iter_lines():
                    if not line:
                         # End of event
                         if current_event:
                             if current_event.get('event') == 'message':
                                 try:
                                     data_str = current_event.get('data')
                                     data = json.loads(data_str)
                                     return data.get('result')
                                 except json.JSONDecodeError as e:
                                     logger.error(f"Failed to decode JSON from SSE message: {e}")
                             current_event = {}
                         continue

                    field, value = self._parse_sse_line(line)
                    if field:
                        if field == 'data':
                            if 'data' in current_event:
                                current_event['data'] += "\n" + value
                            else:
                                current_event['data'] = value
                        else:
                            current_event[field] = value
                
                logger.error("SSE stream ended without valid response")
                return None

            try:
                data = response.json()
            except Exception as json_err:
                logger.error(f"MCP Response is not JSON. Status: {response.status_code}. Content: {response.text[:500]}")
                
                # Fallback: check if content looks like SSE even if header is wrong
                if 'event: message' in response.text:
                    logger.info("Content looks like SSE, trying to parse manually...")
                    for line in response.iter_lines(decode_unicode=True):
                         if line.startswith('data: '):
                             json_str = line[6:]
                             try:
                                 data = json.loads(json_str)
                                 return data.get('result')
                             except:
                                 pass
                raise json_err

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
        # base_url = base_url # Keep full URL
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
    else:
        print("Failed to list tools.")

if __name__ == "__main__":
    main()
