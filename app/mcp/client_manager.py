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
        # 使用 Client(url) 上下文管理器时，fastmcp 会自动处理连接和断开
        # 如果服务器不支持 DELETE，断开时可能会报错，我们需要捕获这个错误
        # 以免影响工具调用的结果返回
        
        # 1. Manually manage lifecycle to suppress cleanup errors
        client = Client(url)
        try:
            await client.__aenter__()
            # Call tool
            result = await client.call_tool(tool_name, **arguments)
            return result
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            raise e
        finally:
            try:
                # 尝试优雅关闭，如果服务器不支持 DELETE (405)，忽略错误
                await client.__aexit__(None, None, None)
            except Exception as e:
                # Log as warning but don't fail the operation
                logger.warning(f"Error closing MCP session (likely benign 405): {e}")

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
            # Note: _list_tools_async also uses context manager, we might want to wrap it too
            # if listing tools also fails on exit. But typically we care more about call_tool reliability.
            # Let's wrap list_tools similarly if needed, or rely on _list_tools_async implementation.
            # For now, keeping as is, but if list_tools fails on exit, we should fix it too.
            
            # Let's use a safe wrapper for list_tools as well
            async def safe_list_tools(url):
                client = Client(url)
                try:
                    await client.__aenter__()
                    return await client.list_tools()
                finally:
                    try:
                        await client.__aexit__(None, None, None)
                    except Exception:
                        pass

            tools_list = self._run_async(safe_list_tools(url))
            
            # Update DB
            server.tools_count = len(tools_list)
            server.last_check_at = db.func.now()
            server.status = 'active'
            
            # Clear old tools
            MCPTool.query.filter_by(server_id=server.id).delete()
            
            for tool in tools_list:
                if hasattr(tool, 'inputSchema'):
                    input_schema = tool.inputSchema
                elif hasattr(tool, 'parameters'):
                    if hasattr(tool.parameters, 'model_json_schema'):
                        input_schema = tool.parameters.model_json_schema()
                    elif isinstance(tool.parameters, dict):
                        input_schema = tool.parameters
                    else:
                        input_schema = {}
                else:
                    input_schema = {}
                
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
        
        # Result handling
        # If result is list of Content objects, convert to string
        if isinstance(result, list):
            final_text = ""
            for block in result:
                if hasattr(block, 'text'):
                    final_text += block.text + "\n"
                elif isinstance(block, dict) and 'text' in block: # Fallback if dict
                    final_text += block['text'] + "\n"
                else:
                    final_text += str(block) + "\n"
            return final_text.strip()
        
        return result

# Global Instance
mcp_manager = MCPClientManager()
