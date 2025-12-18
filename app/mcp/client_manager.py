import logging
import asyncio
from fastmcp import Client
from app.models.models import db, MCPServer, MCPTool

logger = logging.getLogger(__name__)

class MCPClientManager:
    _instance = None
    _clients = {} # server_key -> FastMCP Client instance (if we need to cache them, but they are async context managers)
    # Actually, FastMCP Client is designed to be used in 'async with'.
    # If we want to keep connections open (SSE), we need to maintain the client instance and its loop/task.
    # However, for this integration in a synchronous Flask app, maybe we just connect-on-demand for now,
    # OR we use a global event loop thread?
    # Given the previous implementation was request/response based (mostly), 
    # and FastMCP Client can handle single requests if initialized properly.
    # But wait, FastMCP client uses `httpx` and `anyio`.

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MCPClientManager, cls).__new__(cls)
        return cls._instance

    def _run_async(self, coro):
        """Helper to run async code in sync context"""
        try:
            return asyncio.run(coro)
        except RuntimeError:
            # If there is already an event loop running (e.g. uvicorn/asyncio based server), 
            # we should use it? But we are in Flask (WSGI usually).
            # If we are in a thread with an existing loop?
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)

    async def _list_tools_async(self, url, auth_token=None):
        # FastMCP Client constructor takes 'auth' but expects httpx.Auth or similar?
        # Let's check signature again: auth: "httpx.Auth | Literal['oauth'] | str | None"
        # If it's a bearer token, we might need to pass it as header?
        # FastMCP documentation says 'auth' param. If string, what does it do?
        # If we look at fastmcp source or docs...
        # Let's try passing auth token if provided.
        # But wait, the Huawei URL has token in query param.
        # If auth_token is separate, we might need to use it.
        # For now, let's assume URL handles auth if token is in it.
        
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
            if server.auth_token and 'token=' not in url:
                # If auth token exists and not in URL, maybe append or header?
                # For now let's rely on user putting token in URL or handle basic cases.
                pass

            # Run async list_tools
            tools_list = self._run_async(self._list_tools_async(url))
            
            # Update DB
            server.tools_count = len(tools_list)
            server.last_check_at = db.func.now()
            server.status = 'active'
            
            # Clear old tools
            MCPTool.query.filter_by(server_id=server.id).delete()
            
            for tool in tools_list:
                # FastMCP tool object has name, description, parameters (model)
                # We need to convert pydantic model to dict schema
                input_schema = tool.parameters.model_json_schema() if tool.parameters else {}
                
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
        
        # Result might be a text, or object?
        # FastMCP client.call_tool returns the result directly.
        # If it's a CallToolResult from mcp, we might need to extract content.
        # FastMCP wrapper usually returns the parsed value if possible.
        # Let's inspect the result type if needed, but usually it returns the list of content blocks.
        
        # If result is list of TextContent/ImageContent etc.
        # We should format it for the agent.
        if isinstance(result, list):
            # Concatenate text blocks?
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
