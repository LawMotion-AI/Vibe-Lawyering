"""
中国裁判文书网 MCP Server
基于 Model Context Protocol (MCP) 协议，为 AI 工具提供裁判文书检索能力。

依赖：
    pip install mcp httpx beautifulsoup4
"""

import asyncio
import json
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    CallToolResult,
    ListToolsResult,
)

from config import BASE_URL, REQUEST_TIMEOUT, MAX_RESULTS

app = Server("judgment-docs")


@app.list_tools()
async def list_tools() -> ListToolsResult:
    return ListToolsResult(tools=[
        Tool(
            name="search_judgments",
            description="在中国裁判文书网搜索裁判文书。支持按关键词、法院、日期、案件类型筛选。",
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "搜索关键词"},
                    "court": {"type": "string", "description": "法院名称，可留空"},
                    "date_from": {"type": "string", "description": "裁判日期起始 YYYY-MM-DD"},
                    "date_to": {"type": "string", "description": "裁判日期截止 YYYY-MM-DD"},
                    "case_type": {
                        "type": "string",
                        "enum": ["民事", "刑事", "行政", "执行", "国家赔偿", ""],
                        "description": "案件类型"
                    },
                    "page": {"type": "integer", "default": 1}
                },
                "required": ["keyword"]
            }
        ),
        Tool(
            name="get_judgment",
            description="根据文书 ID 获取裁判文书全文。",
            inputSchema={
                "type": "object",
                "properties": {"doc_id": {"type": "string", "description": "裁判文书唯一 ID"}},
                "required": ["doc_id"]
            }
        ),
        Tool(
            name="get_case_summary",
            description="获取案件结构化摘要，包括当事人、裁判结果、核心争议点。",
            inputSchema={
                "type": "object",
                "properties": {"doc_id": {"type": "string"}},
                "required": ["doc_id"]
            }
        ),
        Tool(
            name="list_courts",
            description="列出法院列表，支持按省份和层级筛选。",
            inputSchema={
                "type": "object",
                "properties": {
                    "province": {"type": "string", "description": "省份名称，可留空"},
                    "level": {
                        "type": "string",
                        "enum": ["最高法院", "高级法院", "中级法院", "基层法院", ""]
                    }
                }
            }
        )
    ])


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
    if name == "search_judgments":
        return await search_judgments(**arguments)
    elif name == "get_judgment":
        return await get_judgment(**arguments)
    elif name == "get_case_summary":
        return await get_case_summary(**arguments)
    elif name == "list_courts":
        return await list_courts(**arguments)
    return CallToolResult(content=[TextContent(type="text", text=f"未知工具: {name}")])


async def search_judgments(keyword: str, court="", date_from="", date_to="", case_type="", page=1) -> CallToolResult:
    params = {k: v for k, v in {"searchWord": keyword, "courtName": court, "startDate": date_from,
              "endDate": date_to, "caseType": case_type, "pageNum": page, "pageSize": MAX_RESULTS}.items() if v}
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.get(f"{BASE_URL}/search", params=params)
            resp.raise_for_status()
            return CallToolResult(content=[TextContent(type="text", text=json.dumps(resp.json(), ensure_ascii=False, indent=2))])
    except Exception as e:
        return CallToolResult(content=[TextContent(type="text", text=f"搜索失败: {e}")])


async def get_judgment(doc_id: str) -> CallToolResult:
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.get(f"{BASE_URL}/detail", params={"docId": doc_id})
            resp.raise_for_status()
            return CallToolResult(content=[TextContent(type="text", text=json.dumps(resp.json(), ensure_ascii=False, indent=2))])
    except Exception as e:
        return CallToolResult(content=[TextContent(type="text", text=f"获取文书失败: {e}")])


async def get_case_summary(doc_id: str) -> CallToolResult:
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.get(f"{BASE_URL}/summary", params={"docId": doc_id})
            resp.raise_for_status()
            return CallToolResult(content=[TextContent(type="text", text=json.dumps(resp.json(), ensure_ascii=False, indent=2))])
    except Exception as e:
        return CallToolResult(content=[TextContent(type="text", text=f"获取摘要失败: {e}")])


async def list_courts(province="", level="") -> CallToolResult:
    courts = [
        {"name": "最高人民法院", "level": "最高法院", "province": "全国"},
        {"name": "北京市高级人民法院", "level": "高级法院", "province": "北京"},
        {"name": "广东省高级人民法院", "level": "高级法院", "province": "广东"},
        {"name": "上海市高级人民法院", "level": "高级法院", "province": "上海"},
    ]
    if province:
        courts = [c for c in courts if c["province"] in (province, "全国")]
    if level:
        courts = [c for c in courts if c["level"] == level]
    return CallToolResult(content=[TextContent(type="text", text=json.dumps(courts, ensure_ascii=False, indent=2))])


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
