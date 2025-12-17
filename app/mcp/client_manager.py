import json
import logging
import threading
import time
import requests
import sseclient
from urllib.parse import urljoin
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
                client = sseclient.SSEClient(response)
                
                # Wait for the 'endpoint' event
                for event in client.events():
                    if event.event == 'endpoint':
                        self.post_endpoint = urljoin(self.base_url, event.data)
                        self.is_connected = True
                        logger.info(f"MCP Client {self.server_key} connected. Endpoint: {self.post_endpoint}")
                        # In a real implementation, we might need to keep this thread alive 
                        # to receive other events, but for now we just want the endpoint.
                        # Some servers might require the connection to stay open.
                        # For this POC, we'll break after getting the endpoint.
                        break
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
            response = requests.post(self.post_endpoint, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
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
