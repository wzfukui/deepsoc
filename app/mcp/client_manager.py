import logging
import asyncio
import json
from fastmcp import Client
from app.models.models import db, MCPServer, MCPTool

logger = logging.getLogger(__name__)

class MCPClientManager:
    _instance = None
    _clients = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MCPClientManager, cls).__new__(cls)
        return cls._instance

    def _run_async(self, coro):
        """Helper to run async code in sync context"""
        try:
            return asyncio.run(coro)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)

    async def _list_tools_async(self, url, auth_token=None):
        async with Client(url) as client:
            return await client.list_tools()

    async def _call_tool_async(self, url, tool_name, arguments):
        async with Client(url) as client:
            return await client.call_tool(tool_name, **arguments)

    def sync_all_servers(self, app):
        """
        Syncs all enabled servers from DB.
        """
        logger.info("Syncing MCP Servers (FastMCP)...")
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
        # Use FastMCP to list tools
        try:
            # Prepare URL
            url = server.base_url
            
            # Run async list_tools
            tools_list = self._run_async(self._list_tools_async(url))
            
            # Update DB
            server.tools_count = len(tools_list)
            server.last_check_at = db.func.now()
            server.status = 'active'
            
            # Clear old tools
            MCPTool.query.filter_by(server_id=server.id).delete()
            
            for tool in tools_list:
                # Based on MCP spec and fastmcp behavior:
                # tool.inputSchema contains the JSON schema for arguments
                
                # Check for inputSchema (standard MCP) or fallback to parameters (FastMCP model)
                if hasattr(tool, 'inputSchema'):
                    input_schema = tool.inputSchema
                elif hasattr(tool, 'parameters'):
                    # FastMCP Tool object usually wraps Pydantic model in parameters
                    if hasattr(tool.parameters, 'model_json_schema'):
                        input_schema = tool.parameters.model_json_schema()
                    elif isinstance(tool.parameters, dict):
                        input_schema = tool.parameters
                    else:
                        input_schema = {}
                else:
                    input_schema = {}
                
                # Ensure input_schema is a dict (json serializable)
                if not isinstance(input_schema, dict):
                    input_schema = {}

                new_tool = MCPTool(
                    server_id=server.id,
                    name=tool.name,
                    description=tool.description,
                    input_schema=input_schema
                )
                db.session.add(new_tool)
                
            db.session.commit()
            logger.info(f"Synced server {server.name}: {len(tools_list)} tools found.")
            
        except Exception as e:
            logger.error(f"Error syncing server {server.server_key}: {e}")
            raise e

    def get_all_tools_definitions(self):
        """
        Returns OpenAI-compatible tool definitions for all active tools in DB.
        """
        tools = []
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
        tool = MCPTool.query.filter_by(name=tool_name).first()
        if not tool:
            raise ValueError(f"Tool {tool_name} not found.")
            
        server = MCPServer.query.get(tool.server_id)
        if not server:
            raise ValueError(f"Server for tool {tool_name} not found.")
            
        logger.info(f"Executing tool {tool_name} on server {server.name} (FastMCP)")
        
        # Execute
        result = self._run_async(self._call_tool_async(server.base_url, tool_name, arguments))
        
        # Helper to extract text content
        if isinstance(result, list):
            final_text = ""
            for block in result:
                if hasattr(block, 'text'):
                    final_text += block.text + "\n"
                else:
                    final_text += str(block) + "\n"
            return final_text.strip()
        
        return result

# Global Instance
mcp_manager = MCPClientManager()
