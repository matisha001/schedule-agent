"""赛事问数助手 · MCP 服务（MCPServer 2.x 实现）

把现有 FastAPI 后端（main.py）的赛事 API 封装为 MCP 工具，
供任何支持 MCP 的客户端（Claude Desktop / Cursor / 豆包等）调用，扩展现有赛事问数助手的功能边界。

架构：
  外部 MCP 客户端 ⇄(stdio / streamable-http)⇄ 本服务(MCPServer 2.x)
        ⇄(httpx HTTP)⇄ 赛事后端 http://localhost:8000（复用其权限矩阵）

运行（项目根目录下）：
  uv run python -m app.mcp.server                    # 默认 stdio 传输
  uv run python -m app.mcp.server --transport streamable-http   # HTTP 传输（可选）

环境变量（统一从项目根目录 .env 加载，见根 .env.example 的 MCP 配置段）：
  TOURNAMENT_API_BASE  后端地址，默认 http://localhost:8000
  TOURNAMENT_API_TOKEN 预置登录 token（可选；未登录按 guest 权限，仅公开数据）
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv

# 统一从项目根目录 .env 读取（app/mcp 不维护独立 .env）
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from app.mcp.backend import TournamentBackend

API_BASE = os.getenv("TOURNAMENT_API_BASE", "http://localhost:8000").rstrip("/")
INITIAL_TOKEN = os.getenv("TOURNAMENT_API_TOKEN", "")

backend = TournamentBackend(base_url=API_BASE, token=INITIAL_TOKEN)


def build_server():
    from mcp.server.mcpserver import MCPServer

    server = MCPServer(
        name="tournament-agent",
        title="赛事问数助手 MCP 服务",
        version="0.1.0",
        description=(
            "提供赛事问数助手能力：查询赛事/阶段/队伍/选手/对局（含比分）等结构化数据，"
            "以及预制问数提示词。权限与后端一致：未登录仅公开数据，"
            "可通过环境变量 TOURNAMENT_API_TOKEN 注入登录 token 获得角色权限。"
        ),
    )

    @server.tool(name="get_me", title="当前用户信息", description="返回当前登录用户信息（未登录返回 guest 提示）。")
    async def get_me() -> str:
        return json.dumps(await backend.me(), ensure_ascii=False, default=str)

    @server.tool(
        name="list_tournaments",
        title="赛事列表",
        description="赛事列表。scope=published 返回已发布公开赛事；scope=mine 返回当前用户创建的赛事（需登录 token）。",
    )
    async def list_tournaments(scope: str = "published") -> str:
        return json.dumps(await backend.list_tournaments(scope), ensure_ascii=False, default=str)

    @server.tool(
        name="get_tournament",
        title="赛事详情",
        description="赛事详情：基础配置 + 阶段列表 + 队伍列表（含选手）+ 我的队伍。",
    )
    async def get_tournament(tournament_id: int) -> str:
        return json.dumps(await backend.get_tournament(tournament_id), ensure_ascii=False, default=str)

    @server.tool(
        name="list_phases",
        title="阶段列表",
        description="某赛事的阶段列表（名称/起止时间/状态）。",
    )
    async def list_phases(tournament_id: int) -> str:
        return json.dumps(await backend.list_phases(tournament_id), ensure_ascii=False, default=str)

    @server.tool(
        name="list_teams",
        title="队伍列表",
        description="某赛事的队伍列表（含选手成员）。",
    )
    async def list_teams(tournament_id: int) -> str:
        return json.dumps(await backend.list_teams(tournament_id), ensure_ascii=False, default=str)

    @server.tool(
        name="my_tournaments",
        title="我报名的赛事",
        description="当前用户报名参加的赛事列表（需登录 token）。",
    )
    async def my_tournaments() -> str:
        return json.dumps(await backend.my_tournaments(), ensure_ascii=False, default=str)

    @server.tool(
        name="list_schedules",
        title="对局/赛程列表",
        description="某赛事的对局列表（轮次/BO/双方队伍/比分/状态，已翻译队伍名与阶段名）。",
    )
    async def list_schedules(tournament_id: int) -> str:
        return json.dumps(await backend.list_schedules(tournament_id), ensure_ascii=False, default=str)

    @server.tool(
        name="list_presets",
        title="预制问数提示词",
        description="按当前登录态/角色返回服务端预制问数提示词（未登录为 guest 公开 4 条）。",
    )
    async def list_presets() -> str:
        return json.dumps(await backend.list_presets(), ensure_ascii=False, default=str)

    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="赛事问数助手 MCP 服务")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="MCP 传输方式（默认 stdio）",
    )
    parser.add_argument("--host", default="127.0.0.1", help="streamable-http 监听地址")
    parser.add_argument("--port", type=int, default=8899, help="streamable-http 监听端口")
    args = parser.parse_args()

    server = build_server()
    if args.transport == "stdio":
        server.run(transport="stdio")
    else:
        server.run(transport="streamable-http", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
