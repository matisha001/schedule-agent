# 赛事问数助手 · MCP 服务

把现有赛事后端（FastAPI `main.py`）的**赛事 API** 封装为 MCP 工具（MCPServer 2.x 实现），
供任何支持 MCP 的客户端调用，扩展现有赛事问数助手的能力边界（外部 Agent / IDE / 聊天客户端均可接入）。

```
外部 MCP 客户端 ⇄ stdio / streamable-http ⇄ 本服务 (MCPServer 2.x, Python)
        ⇄ httpx HTTP ⇄ 赛事后端 http://localhost:8000
```

- **强制鉴权**：必须配置 `TOURNAMENT_API_TOKEN`（登录接口返回的 token），未配置则 MCP 服务拒绝启动。所有调用以该 token 对应用户身份执行，权限与后端一致。
- **比赛主流程**：创建赛事→发布→报名→审核→排对局→录比分，以及用户资料（昵称/密码）修改。

## 快速开始

```bash
# 1. 启动赛事后端（前提，端口 8000）
uv run uvicorn main:app --reload

# 2. 启动本 MCP 服务（stdio，默认给 MCP 客户端用）
uv run python -m app.mcp.server

# 可选：streamable-http 模式
uv run python -m app.mcp.server --transport streamable-http --host 127.0.0.1 --port 8899
```

环境变量（统一从**项目根目录 `.env`** 读取，模板见根目录 `.env.example` 的 MCP 配置段）：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `TOURNAMENT_API_BASE` | `http://localhost:8000` | 赛事后端地址 |
| `TOURNAMENT_API_TOKEN` | **无（必填）** | 登录接口返回的 token；未配置则服务拒绝启动 |

## 提供的 MCP 工具

### 读操作（按登录角色）

| 工具 | 说明 |
|---|---|
| `get_me()` | 当前用户信息 |
| `update_profile(nickname)` | **修改昵称** |
| `update_password(old, new)` | **修改密码** |
| `list_tournaments(scope)` | 赛事列表（published / mine） |
| `get_tournament(tournament_id)` | 赛事详情（配置+阶段+队伍+我的队伍） |
| `list_phases(tournament_id)` | 阶段列表 |
| `list_teams(tournament_id)` | 队伍列表（含选手） |
| `my_tournaments()` | 我报名的赛事 |
| `list_schedules(tournament_id)` | 对局/赛程列表（含比分） |
| `list_presets()` | 预制问数提示词（按角色过滤） |

### 比赛主流程（写操作，需登录 token 且为对应角色/创建者）

| 工具 | 说明 | 后端 API |
|---|---|---|
| `create_tournament(...)` | **快速创建赛事**（草稿，需再发布） | `POST /api/tournaments` |
| `transition_tournament(id, action)` | **赛事状态流转** publish/open/close/start/finish | `POST /api/tournaments/{id}/transition` |
| `create_phase(id, name, ...)` | 创建阶段 | `POST /api/tournaments/{id}/phases` |
| `register_team(id, name, players)` | **快速报名**（选手自主） | `POST /api/tournaments/{id}/teams` |
| `register_team_by_organizer(id, name, players)` | **办赛者代报名** | `POST /api/tournaments/{id}/admin-teams` |
| `review_team(team_id, status)` | **队伍审核**（确认/驳回） | `PATCH /api/teams/{id}/status` |
| `create_schedule(id, home, away, ...)` | **创建对局** | `POST /api/tournaments/{id}/schedules` |
| `update_schedule(id, score, ...)` | **录入比分/更新对局** | `PATCH /api/schedules/{id}` |

> 写操作权限与后端一致：创建/流转/审核/对局仅赛事创建者；自主报名需赛事处于报名中且非该赛事创建者。

## 接入 MCP 客户端

### Claude Desktop（`~/Library/Application Support/Claude/claude_desktop_config.json`）

```json
{
  "mcpServers": {
    "tournament-agent": {
      "command": "uv",
      "args": ["--directory", "/Users/caoyankui/code/schedule-agent", "run", "python", "-m", "app.mcp.server"],
      "env": {
        "TOURNAMENT_API_BASE": "http://localhost:8000"
      }
    }
  }
}
```

### Cursor（`.cursor/mcp.json`）

```json
{
  "mcpServers": {
    "tournament-agent": {
      "command": "uv",
      "args": ["--directory", "/Users/caoyankui/code/schedule-agent", "run", "python", "-m", "app.mcp.server"]
    }
  }
}
```

### 任意 MCP 客户端（stdio 命令）

```
uv --directory /Users/caoyankui/code/schedule-agent run python -m app.mcp.server
```

## 典型用法示例

> 查看已发布赛事：`list_tournaments(scope="published")`
> 查看某赛事赛程：`list_schedules(tournament_id=1)`
> 查看某赛事队伍：`list_teams(tournament_id=1)`

`list_schedules` 返回 JSON 数组：

```json
[
  {
    "id": 1,
    "round": 1,
    "round_name": "小组赛",
    "bo": 3,
    "home_team_name": "A队",
    "away_team_name": "B队",
    "home_score": 2,
    "away_score": 1,
    "status_label": "已结束"
  }
]
```

## 目录结构

```
app/mcp/
├── server.py       # MCPServer 2.x 定义 + 入口（stdio / streamable-http）
├── backend.py      # 赛事后端 HTTP 客户端
└── __init__.py
```

依赖挂在主项目 `pyproject.toml`（`mcp>=2.2.0`，httpx/python-dotenv 已随主依赖安装）。

## 与现有后端的对应关系

| MCP 工具 | 后端 API |
|---|---|
| `get_me` | `GET /api/auth/me` |
| `list_tournaments` / `get_tournament` | `GET /api/tournaments[?scope=]` / `GET /api/tournaments/{id}` |
| `list_phases` | `GET /api/tournaments/{id}/phases` |
| `list_teams` | `GET /api/tournaments/{id}/teams` |
| `my_tournaments` | `GET /api/me/tournaments` |
| `list_schedules` | `GET /api/tournaments/{id}/schedules` |
| `list_presets` | `GET /api/query/presets` |

API 完整清单见 `docs/api-inventory.md`。
