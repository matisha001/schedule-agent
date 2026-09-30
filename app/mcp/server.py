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
  TOURNAMENT_API_TOKEN 必填！登录接口返回的 token；未配置时服务拒绝启动
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

if not INITIAL_TOKEN:
    raise SystemExit(
        "MCP 服务强制要求 API_TOKEN：请在赛事后端登录接口获取 token，"
        "并配置环境变量 TOURNAMENT_API_TOKEN（见根目录 .env.example 的 MCP 配置段）。"
    )

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

    @server.tool(name="get_me", title="当前用户信息", description="返回当前登录用户（token 对应账号）的信息。")
    async def get_me() -> str:
        return json.dumps(await backend.me(), ensure_ascii=False, default=str)

    @server.tool(
        name="update_profile",
        title="修改昵称",
        description="修改当前登录用户的昵称（1-64 字符）。返回更新后的用户信息。",
    )
    async def update_profile(nickname: str) -> str:
        return json.dumps(await backend.update_profile(nickname), ensure_ascii=False, default=str)

    @server.tool(
        name="update_password",
        title="修改密码",
        description="修改当前登录用户的密码：old_password 为当前密码，new_password 为新密码（6-64 位）。",
    )
    async def update_password(old_password: str, new_password: str) -> str:
        return json.dumps(await backend.update_password(old_password, new_password), ensure_ascii=False, default=str)

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

    # ---------- 比赛主流程（写操作，需登录 token 且为对应角色/创建者） ----------

    @server.tool(
        name="create_tournament",
        title="快速创建赛事",
        description=(
            "创建一场新赛事（当前登录用户为办赛者/创建者）。"
            "必填 name；可选 game/game_maps/team_mode(1团队赛 2个人赛)/start_time/end_time/"
            "reg_start_time/reg_end_time/max_team_members/max_teams/regist_method(1办赛者代报名 2选手自主报名)/"
            "contact_requirement/rule_info。创建后状态为草稿，需再调用 transition_tournament 发布。"
        ),
    )
    async def create_tournament(
        name: str,
        game: str | None = None,
        game_maps: str | None = None,
        team_mode: int = 1,
        start_time: str | None = None,
        end_time: str | None = None,
        reg_start_time: str | None = None,
        reg_end_time: str | None = None,
        max_team_members: int = 5,
        max_teams: int = 16,
        regist_method: int = 1,
        contact_requirement: str | None = None,
        rule_info: str | None = None,
    ) -> str:
        payload = {
            "name": name,
            "game": game,
            "game_maps": game_maps,
            "team_mode": team_mode,
            "start_time": start_time,
            "end_time": end_time,
            "reg_start_time": reg_start_time,
            "reg_end_time": reg_end_time,
            "max_team_members": max_team_members,
            "max_teams": max_teams,
            "regist_method": regist_method,
            "contact_requirement": contact_requirement,
            "rule_info": rule_info,
        }
        return json.dumps(await backend.create_tournament(payload), ensure_ascii=False, default=str)

    @server.tool(
        name="transition_tournament",
        title="赛事状态流转",
        description=(
            "推进赛事状态（仅创建者可操作）：publish(草稿→已发布)、open(开始报名)、close(结束报名)、"
            "start(开始比赛)、finish(结束比赛)。非法流转后端会报错。"
        ),
    )
    async def transition_tournament(tournament_id: int, action: str) -> str:
        return json.dumps(
            await backend.transition_tournament(tournament_id, action), ensure_ascii=False, default=str
        )

    @server.tool(
        name="create_phase",
        title="创建阶段",
        description="为某赛事创建阶段（仅创建者可操作）。name 必填；可选 start_time/end_time。",
    )
    async def create_phase(
        tournament_id: int, name: str, start_time: str | None = None, end_time: str | None = None
    ) -> str:
        payload = {"name": name, "start_time": start_time, "end_time": end_time}
        return json.dumps(await backend.create_phase(tournament_id, payload), ensure_ascii=False, default=str)

    @server.tool(
        name="register_team",
        title="快速报名",
        description=(
            "当前登录用户报名某赛事（需赛事处于报名中）。团队赛 name 为队伍名、players 为队友昵称列表（可选）；"
            "个人赛可不传 name（自动取昵称）。后端约束：办赛者不能报名自己创建的赛事、每人每赛仅一次。"
        ),
    )
    async def register_team(
        tournament_id: int,
        name: str = "",
        players: list[str] | None = None,
    ) -> str:
        payload = {
            "name": name,
            "players": [{"nickname": p, "is_captain": False} for p in (players or [])],
        }
        return json.dumps(await backend.register_team(tournament_id, payload), ensure_ascii=False, default=str)

    @server.tool(
        name="register_team_by_organizer",
        title="办赛者代报名",
        description="办赛者为自己创建的赛事添加队伍（需登录且为该赛事创建者）。name 队伍名必填；players 为队员昵称列表。",
    )
    async def register_team_by_organizer(
        tournament_id: int,
        name: str,
        players: list[str] | None = None,
    ) -> str:
        payload = {
            "name": name,
            "players": [{"nickname": p, "is_captain": False} for p in (players or [])],
        }
        return json.dumps(
            await backend.register_team_by_organizer(tournament_id, payload), ensure_ascii=False, default=str
        )

    @server.tool(
        name="review_team",
        title="队伍审核",
        description="办赛者审核自己赛事的报名队伍：status 0待审核 1已确认 2已驳回 3已取消。确认后队伍内待确认选手一并同意。",
    )
    async def review_team(team_id: int, status: int) -> str:
        return json.dumps(await backend.review_team(team_id, status), ensure_ascii=False, default=str)

    @server.tool(
        name="create_schedule",
        title="创建对局",
        description=(
            "为某赛事创建一场对局（仅创建者可操作）。phase_id 必填（先 create_phase 建阶段或 list_phases 查已有阶段）；"
            "home_team_id/away_team_id 为双方队伍 id（查 list_teams）；"
            "可选 round/round_name/bo(1-9)/is_final/start_time。"
        ),
    )
    async def create_schedule(
        tournament_id: int,
        phase_id: int,
        home_team_id: int,
        away_team_id: int,
        round: int = 1,
        round_name: str | None = None,
        bo: int = 1,
        is_final: bool = False,
        start_time: str | None = None,
    ) -> str:
        payload = {
            "phase_id": phase_id,
            "round": round,
            "round_name": round_name,
            "bo": bo,
            "is_final": is_final,
            "home_team_id": home_team_id,
            "away_team_id": away_team_id,
            "start_time": start_time,
        }
        return json.dumps(await backend.create_schedule(tournament_id, payload), ensure_ascii=False, default=str)

    @server.tool(
        name="update_schedule",
        title="录入比分/更新对局",
        description=(
            "更新对局（仅创建者可操作），用于录入比分与推进对局状态。schedule_id 可查 list_schedules；"
            "home_score/away_score 为双方比分；可选 status 0未开赛 1进行中 2已结束 3已取消。"
        ),
    )
    async def update_schedule(
        schedule_id: int,
        home_score: int,
        away_score: int,
        status: int | None = None,
    ) -> str:
        payload = {"home_score": home_score, "away_score": away_score, "status": status}
        return json.dumps(await backend.update_schedule(schedule_id, payload), ensure_ascii=False, default=str)

    return server


def run_streamable_http(server: "MCPServer", host: str, port: int) -> None:
    """以 streamable-http 模式启动，并挂载 CORS 中间件支持浏览器跨域调用。

    SDK 的 server.run() 无法注入 CORS，因此手动构建 Starlette app：
    - 端点路径固定 /mcp（与 SDK 默认一致）
    - 允许任意来源的浏览器调用（前端 dev server 5173 与第三方 MCP 客户端）
    - expose mcp-session-id / mcp-session-expiry，供浏览器读取会话响应头
    """
    import anyio
    import uvicorn
    from starlette.middleware.cors import CORSMiddleware

    async def serve() -> None:
        app = server.streamable_http_app(streamable_http_path="/mcp")
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["mcp-session-id", "mcp-session-expiry"],
        )
        await uvicorn.Server(uvicorn.Config(app, host=host, port=port)).serve()

    anyio.run(serve)


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
        run_streamable_http(server, args.host, args.port)


if __name__ == "__main__":
    main()
