import asyncio
import logging
import json
from datetime import datetime
from urllib.parse import urlparse

from app.models import db, MCPServer, MCPTool
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
# from mcp.client.stdio import stdio_client # 暂时只支持 SSE/HTTP

logger = logging.getLogger(__name__)

class MCPManager:
    """MCP Server 管理器，负责连接、同步工具和执行工具"""

    @staticmethod
    def get_all_tool_definitions():
        """获取所有可用工具的定义，格式化为 OpenAI Tool 格式"""
        tools = MCPTool.query.join(MCPServer).filter(MCPServer.status == 'enabled').all()
        definitions = []
        for tool in tools:
            server = MCPServer.query.get(tool.server_id)
            # 构造唯一的工具名称：server_key__tool_name
            unique_tool_name = f"{server.server_key}__{tool.name}"
            
            definitions.append({
                "type": "function",
                "function": {
                    "name": unique_tool_name,
                    "description": tool.description or "",
                    "parameters": tool.input_schema
                }
            })
        return definitions

    @staticmethod
    async def _connect_and_list_tools(server: MCPServer):
        """(Internal) 连接 Server 并获取工具列表"""
        if server.transport_type == 'sse' or server.transport_type == 'http':
            # SSE 连接模式
            # 注意：mcp 库的 sse_client 上下文管理器会自动处理连接
            async with sse_client(server.base_url) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    return result.tools
        else:
            raise NotImplementedError(f"Unsupported transport type: {server.transport_type}")

    @staticmethod
    async def _connect_and_call_tool(server: MCPServer, tool_name: str, arguments: dict):
        """(Internal) 连接 Server 并执行工具"""
        if server.transport_type == 'sse' or server.transport_type == 'http':
            async with sse_client(server.base_url) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments)
                    return result
        else:
            raise NotImplementedError(f"Unsupported transport type: {server.transport_type}")

    @classmethod
    def sync_server_tools_sync(cls, server_id):
        """同步指定 Server 的工具列表 (同步包装器)"""
        return asyncio.run(cls.sync_server_tools(server_id))

    @classmethod
    async def sync_server_tools(cls, server_id):
        """同步指定 Server 的工具列表"""
        server = MCPServer.query.get(server_id)
        if not server:
            logger.error(f"Server ID {server_id} not found")
            return False

        try:
            logger.info(f"Syncing tools for server: {server.name} ({server.base_url})")
            tools_list = await cls._connect_and_list_tools(server)
            
            # 更新数据库
            # 先删除该 Server 下的旧工具缓存
            MCPTool.query.filter_by(server_id=server.id).delete()
            
            for tool_data in tools_list:
                # tool_data 是 mcp.types.Tool 对象
                new_tool = MCPTool(
                    server_id=server.id,
                    name=tool_data.name,
                    description=tool_data.description,
                    input_schema=tool_data.inputSchema
                )
                db.session.add(new_tool)
            
            server.tools_count = len(tools_list)
            server.status = 'enabled' # 同步成功则视为可用
            server.last_check_at = datetime.utcnow()
            db.session.commit()
            logger.info(f"Successfully synced {len(tools_list)} tools for server {server.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync tools for server {server.name}: {e}")
            server.status = 'error'
            server.last_check_at = datetime.utcnow()
            db.session.commit()
            return False

    @classmethod
    def execute_tool_sync(cls, unique_tool_name, arguments):
        """执行工具 (同步包装器)"""
        return asyncio.run(cls.execute_tool(unique_tool_name, arguments))

    @classmethod
    async def execute_tool(cls, unique_tool_name, arguments):
        """执行工具"""
        # 解析 server_key 和 tool_name
        try:
            server_key, tool_name = unique_tool_name.split('__', 1)
        except ValueError:
            return {"error": f"Invalid tool name format: {unique_tool_name}"}

        server = MCPServer.query.filter_by(server_key=server_key).first()
        if not server:
            return {"error": f"Server with key {server_key} not found"}

        try:
            logger.info(f"Executing tool {tool_name} on server {server.name}")
            result = await cls._connect_and_call_tool(server, tool_name, arguments)
            
            # result 是 CallToolResult 对象
            output_text = []
            if result.content:
                for content in result.content:
                    if content.type == 'text':
                        output_text.append(content.text)
                    elif content.type == 'image':
                        output_text.append(f"[Image: {content.mimeType}]") # 暂不处理图片
                    elif content.type == 'resource':
                        output_text.append(f"[Resource: {content.uri}]")
            
            final_output = "\n".join(output_text)
            
            if result.isError:
                return {"error": final_output}
            
            return {"result": final_output}

        except Exception as e:
            logger.error(f"Error executing tool {unique_tool_name}: {e}")
            return {"error": str(e)}
