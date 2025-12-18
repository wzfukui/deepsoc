import json
import logging
import threading
import time
import requests
from urllib.parse import urljoin, urlparse, urlunparse, parse_qs, urlencode
from app.models.models import db, MCPServer, MCPTool
from app.services.llm_service import call_llm

logger = logging.getLogger(__name__)

class MCPClient:
    def __init__(self, server_model: MCPServer):
        self.server_key = server_model.server_key
        self.base_url = server_model.base_url
        self.auth_token = server_model.auth_token
        self.transport_type = server_model.transport_type
        self.post_endpoint = None
        self.session_id = None
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
        """
        Connects to the MCP server.
        For SSE, this means establishing the SSE connection to get the POST endpoint.
        """
        if self.transport_type == 'sse':
            try:
                headers = {'Accept': 'text/event-stream'}
                if self.auth_token:
                    headers['Authorization'] = f"Bearer {self.auth_token}"
                
                # We need to stream the response
                response = requests.get(self.base_url, stream=True, headers=headers, timeout=10)
                
                # Handle case where server returns JSON directly (not standard SSE handshake)
                content_type = response.headers.get('Content-Type', '').lower()
                if 'application/json' in content_type:
                    logger.warning(f"MCP Client {self.server_key}: Connect returned JSON, not SSE. Falling back to using base_url as endpoint.")
                    self.post_endpoint = self.base_url
                    self.is_connected = True
                    return

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
                                logger.info(f"MCP Client {self.server_key} connected. Endpoint: {self.post_endpoint}")
                                return
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
                
                # If we exit loop without finding endpoint (and not JSON fallback), connection failed
                if not self.is_connected:
                     logger.warning(f"MCP Client {self.server_key}: SSE stream ended without 'endpoint' event.")
                     
            except Exception as e:
                logger.error(f"Failed to connect to MCP server {self.server_key}: {e}")
                self.is_connected = False
                raise e
        else:
            # Assume HTTP transport where base_url IS the endpoint (simplified)
            self.post_endpoint = self.base_url
            self.is_connected = True

    def list_tools(self):
        if not self.is_connected or not self.post_endpoint:
            self.connect()
            
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 1
        }
        return self._send_request(payload)

    def call_tool(self, tool_name, arguments):
        if not self.is_connected or not self.post_endpoint:
            self.connect()

        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            },
            "id": int(time.time())
        }
        return self._send_request(payload)

    def _send_request(self, payload):
        headers = {'Content-Type': 'application/json'}
        if self.auth_token:
            headers['Authorization'] = f"Bearer {self.auth_token}"
            
        try:
            # Enable streaming to handle SSE responses
            response = requests.post(self.post_endpoint, json=payload, headers=headers, timeout=30, stream=True)
            
            # Check for SSE response
            content_type = response.headers.get('Content-Type', '').lower()
            if 'text/event-stream' in content_type:
                logger.info(f"MCP Response is SSE. Content-Type: {content_type}")
                
                current_event = {}
                for line in response.iter_lines():
                    if not line:
                         # End of event
                         if current_event:
                             if current_event.get('event') == 'message':
                                 try:
                                     data_str = current_event.get('data')
                                     data = json.loads(data_str)
                                     
                                     if 'result' in data:
                                         return data.get('result', {})
                                     elif 'error' in data:
                                         raise Exception(f"MCP JSON-RPC Error: {data['error']}")
                                     
                                     # Keep looking? standard MCP usually has one message response
                                     return data.get('result', {})
                                 except json.JSONDecodeError as e:
                                     logger.error(f"Failed to decode JSON from SSE message: {e}")
                                     raise e
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
                            
                raise Exception("SSE stream ended without valid response")

            # Standard JSON handling
            try:
                data = response.json()
            except Exception as json_err:
                # Handle encoding explicitly for logging to avoid mojibake
                try:
                    content_str = response.content.decode('utf-8', errors='replace')
                except:
                    content_str = str(response.content) # Fallback
                
                logger.error(f"MCP Response is not JSON. Status: {response.status_code}. Content: {content_str[:1000]}")
                
                # Fallback: check if content looks like SSE even if header is wrong
                if 'event: message' in content_str:
                    try:
                        import re
                        match = re.search(r'data: ({.*})', content_str)
                        if match:
                             data = json.loads(match.group(1))
                             return data.get('result', {})
                    except:
                        pass
                
                raise json_err

            if 'error' in data:
                raise Exception(f"MCP JSON-RPC Error: {data['error']}")
                
            return data.get('result', {})
        except Exception as e:
            logger.error(f"MCP Request Failed ({self.server_key}): {e}")
            raise e

class MCPClientManager:
    _instance = None
    _clients = {} # server_key -> MCPClient

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MCPClientManager, cls).__new__(cls)
        return cls._instance

    def sync_all_servers(self, app):
        """
        Syncs all enabled servers from DB, updates tool definitions in DB.
        Needs Flask App context.
        """
        logger.info("Syncing MCP Servers...")
        with app.app_context():
            servers = MCPServer.query.filter_by(status='enabled').all()
            for server in servers:
                try:
                    self.sync_server(server)
                except Exception as e:
                    logger.error(f"Failed to sync server {server.name}: {e}")
                    server.status = 'error'
                    db.session.commit()

    def sync_server(self, server: MCPServer):
        client = MCPClient(server)
        client.connect()
        self._clients[server.server_key] = client
        
        # List Tools
        result = client.list_tools()
        tools_list = result.get('tools', [])
        
        # Update DB
        server.tools_count = len(tools_list)
        server.last_check_at = db.func.now()
        server.status = 'active'
        
        # Clear old tools (simplified)
        MCPTool.query.filter_by(server_id=server.id).delete()
        
        for tool_def in tools_list:
            tool = MCPTool(
                server_id=server.id,
                name=tool_def['name'],
                description=tool_def.get('description'),
                input_schema=tool_def.get('inputSchema')
            )
            db.session.add(tool)
            
        db.session.commit()
        logger.info(f"Synced server {server.name}: {len(tools_list)} tools found.")

    def get_all_tools_definitions(self):
        """
        Returns OpenAI-compatible tool definitions for all active tools in DB.
        """
        tools = []
        # Join query to get server key if needed, but for now just name
        # Assumption: Tool names are unique enough or we prepend server key? 
        # OpenAI requires unique names. Let's prepend server key if collision is risk, 
        # but for now simple mapping.
        
        db_tools = MCPTool.query.all()
        for t in db_tools:
            tools.append({
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.input_schema
                }
            })
        return tools

    def execute_tool(self, tool_name, arguments):
        """
        Finds the server owning the tool and executes it.
        """
        # Find tool in DB to get server_id
        tool = MCPTool.query.filter_by(name=tool_name).first()
        if not tool:
            raise ValueError(f"Tool {tool_name} not found.")
            
        server = MCPServer.query.get(tool.server_id)
        if not server:
            raise ValueError(f"Server for tool {tool_name} not found.")
            
        # Get or Create Client
        if server.server_key not in self._clients:
            # We might need to re-init client if not in memory (e.g. after restart)
            # This requires 'server' object which we have
            self._clients[server.server_key] = MCPClient(server)
            
        client = self._clients[server.server_key]
        
        logger.info(f"Executing tool {tool_name} on server {server.name}")
        result = client.call_tool(tool_name, arguments)
        return result

# Global Instance
mcp_manager = MCPClientManager()
