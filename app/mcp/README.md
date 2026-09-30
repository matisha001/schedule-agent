# 赛事问数助手 · MCP 服务

把现有赛事后端（FastAPI `main.py`）的**赛事 API** 封装为 MCP 工具（MCPServer 2.x 实现），
供任何支持 MCP 的客户端调用，扩展现有赛事问数助手的能力边界（外部 Agent / IDE / 聊天客户端均可接入）。

```
外部 MCP 客户端 ⇄ stdio / streamable-http ⇄ 本服务 (MCPServer 2.x, Python)
        ⇄ httpx HTTP ⇄ 赛事后端 http://localhost:8000
```

- **复用后端权限矩阵**：未登录 = guest（仅公开数据）；通过环境变量注入登录 token 后按角色（player/organizer/operator/super_admin）访问。
- **只读能力**：提供赛事/阶段/队伍/选手/对局的结构化查询与预制提示词，不暴露问数 Agent 与登录写操作。

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
| `TOURNAMENT_API_TOKEN` | 空 | 预置登录 token；不填则游客身份（仅公开数据） |

## 提供的 MCP 工具

| 工具 | 说明 |
|---|---|
| `get_me()` | 当前用户信息 |
| `list_tournaments(scope)` | 赛事列表（published / mine） |
| `get_tournament(tournament_id)` | 赛事详情（配置+阶段+队伍+我的队伍） |
| `list_phases(tournament_id)` | 阶段列表 |
| `list_teams(tournament_id)` | 队伍列表（含选手） |
| `my_tournaments()` | 我报名的赛事（需登录 token） |
| `list_schedules(tournament_id)` | 对局/赛程列表（含比分） |
| `list_presets()` | 预制问数提示词（按角色过滤） |

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
