"""
[数据库名称] MCP Server 模板

替换说明：
1. 将所有 <YOUR_DB_NAME> 替换为实际数据库名
2. 在 list_tools() 中定义你的工具
3. 在 call_tool() 中实现工具逻辑
4. 更新 config.example.py 中的配置项
"""

import asyncio
import json
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, CallToolResult, ListToolsResult

from config import BASE_URL, REQUEST_TIMEOUT

app = Server("<YOUR_DB_NAME>")


@app.list_tools()
async def list_tools() -> ListToolsResult:
    return ListToolsResult(tools=[
        Tool(
            name="search",
            description="[描述该工具做什么，何时使用]",
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "搜索关键词"}
                },
                "required": ["keyword"]
            }
        ),
    ])


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
    if name == "search":
        return await search(**arguments)
    return CallToolResult(content=[TextContent(type="text", text=f"未知工具: {name}")])


async def search(keyword: str, **kwargs) -> CallToolResult:
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.get(f"{BASE_URL}/search", params={"q": keyword, **kwargs})
            resp.raise_for_status()
            return CallToolResult(content=[
                TextContent(type="text", text=json.dumps(resp.json(), ensure_ascii=False, indent=2))
            ])
    except Exception as e:
        return CallToolResult(content=[TextContent(type="text", text=f"请求失败: {e}")])


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
