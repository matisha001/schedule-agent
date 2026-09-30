# 赛事管理 Agent · API 清单

> 生成时间：2026-09-30。对应代码：`main.py` + `app/api/routers/*`，服务端口 `http://localhost:8000`。
> 用途：作为 MCP 服务（`mcp_server/`）封装现有后端的参考底稿；也便于前端/第三方接入。

## 一、通用约定

| 项 | 约定 |
|---|---|
| Base URL | `http://localhost:8000` |
| 鉴权 | `Authorization: Bearer <token>`；token 由 `POST /api/auth/login` 获取，HMAC-SHA256 无状态签名，默认 7 天有效 |
| 登录态 | 多数接口可选登录（未登录按 guest 角色 / 公开数据）；写操作（创建/更新/删除）必须登录 |
| 角色 | `guest`（未登录）/ `player`（玩家）/ `organizer`（办赛者）/ `operator`（运营）/ `super_admin`（超管） |
| 问数权限 | `POST /api/query` 按角色注入行级/表级/列级约束，未登录仅公开数据 |
| 日期格式 | ISO 8601（如 `2026-09-30T10:00:00`） |
| 错误 | 非 2xx 时 `{"detail": "错误说明"}` |

## 二、接口总览

| # | 模块 | 方法 & 路径 | 鉴权 | 说明 |
|---|---|---|---|---|
| 1 | Health | `GET /health` | 无 | 健康检查 |
| 2 | Auth | `POST /api/auth/login` | 无 | 手机号+密码登录（新号自动注册） |
| 3 | Auth | `GET /api/auth/me` | 登录 | 当前用户信息 |
| 4 | Auth | `GET /api/auth/bootstrap/status` | 无 | 超管初始化状态 |
| 5 | Auth | `POST /api/auth/bootstrap` | 无 | 凭初始化码创建超管 |
| 6 | Admin | `GET /api/admin/users?page=&size=` | 超管 | 用户分页列表 |
| 7 | Admin | `PATCH /api/admin/users/{id}/role` | 超管 | 修改用户角色 |
| 8 | Tournament | `GET /api/tournaments?scope=published\|mine` | 可选 | 赛事列表（公开/我的） |
| 9 | Tournament | `POST /api/tournaments` | 登录 | 创建赛事 |
| 10 | Tournament | `GET /api/tournaments/{id}` | 可选 | 赛事详情（含阶段/队伍/赛程汇总） |
| 11 | Tournament | `PUT /api/tournaments/{id}` | 创建者 | 更新赛事 |
| 12 | Tournament | `DELETE /api/tournaments/{id}` | 创建者 | 删除赛事（级联） |
| 13 | Tournament | `POST /api/tournaments/{id}/transition` | 创建者 | 状态流转 publish/open/close/start/finish |
| 14 | Tournament | `GET /api/tournaments/{id}/phases` | 可选 | 阶段列表 |
| 15 | Tournament | `POST /api/tournaments/{id}/phases` | 创建者 | 创建阶段 |
| 16 | Tournament | `PUT /api/tournaments/phases/{phase_id}` | 创建者 | 更新阶段 |
| 17 | Tournament | `DELETE /api/tournaments/phases/{phase_id}` | 创建者 | 删除阶段 |
| 18 | Registration | `GET /api/me/tournaments` | 登录 | 我报名的赛事（含我的队伍） |
| 19 | Registration | `GET /api/tournaments/{id}/teams` | 可选 | 队伍列表（含选手） |
| 20 | Registration | `POST /api/tournaments/{id}/teams` | 登录 | 选手自主报名 |
| 21 | Registration | `POST /api/tournaments/{id}/admin-teams` | 创建者 | 办赛者代报名 |
| 22 | Registration | `PATCH /api/teams/{id}/status` | 创建者 | 队伍审核（0待审 1确认 2驳回 3取消） |
| 23 | Registration | `DELETE /api/teams/{id}` | 创建者 | 删除队伍 |
| 24 | Registration | `POST /api/teams/{id}/players` | 创建者 | 添加选手 |
| 25 | Registration | `PATCH /api/players/{id}/captain` | 创建者 | 设为队长 |
| 26 | Registration | `PATCH /api/players/{id}/status` | 创建者 | 选手状态 AGREED/REJECTED |
| 27 | Registration | `DELETE /api/players/{id}` | 创建者 | 删除选手 |
| 28 | Schedule | `GET /api/tournaments/{id}/schedules` | 可选 | 对局列表（含队名/阶段名） |
| 29 | Schedule | `POST /api/tournaments/{id}/schedules` | 创建者 | 创建对局 |
| 30 | Schedule | `PATCH /api/schedules/{id}` | 创建者 | 更新对局（含比分） |
| 31 | Schedule | `DELETE /api/schedules/{id}` | 创建者 | 删除对局 |
| 32 | Query | `POST /api/query` | 可选 | **问数 Agent**（SSE 流式） |
| 33 | Query | `GET /api/query/presets` | 可选 | 预制提示词（按角色过滤） |

## 三、核心接口明细

### 3.1 登录 `POST /api/auth/login`

请求：
```json
{ "phone": "13800138000", "password": "123456" }
```
响应 200：
```json
{
  "token": "eyJ...",
  "user": { "id": 1, "nickname": "玩家8000", "phone": "13800138000", "role": "player", "created_at": "..." }
}
```
> 新手机号自动注册；历史无密码用户首次登录自动认领。密码错误统一 401「手机号或密码错误」。

### 3.2 赛事列表 `GET /api/tournaments?scope=published`

响应 200（`scope=mine` 需登录，未登录 401）：
```json
[
  {
    "id": 1, "name": "秋季赛", "game": "LOL", "game_maps": null,
    "team_mode": 1, "start_time": null, "end_time": null,
    "reg_start_time": null, "reg_end_time": null,
    "max_team_members": 5, "max_teams": 16, "regist_method": 1,
    "contact_requirement": null, "rule_info": null,
    "status": 2, "created_by": 1, "created_at": "...",
    "phase_count": 3, "team_count": 8
  }
]
```
> `status`：0草稿 1已发布 2报名中 3比赛中 4已结束。

### 3.3 赛事详情 `GET /api/tournaments/{id}`

响应 200：赛事基础字段 + `phases`（阶段数组）+ `teams`（队伍数组，含 `players`）+ `my_team`（当前用户队伍，可选）。

### 3.4 创建赛事 `POST /api/tournaments`

请求体（必填仅 `name`）：
```json
{
  "name": "秋季赛",
  "game": "LOL",
  "game_maps": "召唤师峡谷",
  "team_mode": 1,
  "start_time": null, "end_time": null,
  "reg_start_time": null, "reg_end_time": null,
  "max_team_members": 5, "max_teams": 16,
  "regist_method": 1,
  "contact_requirement": null, "rule_info": null
}
```

### 3.5 状态流转 `POST /api/tournaments/{id}/transition`

```json
{ "action": "publish" }
```
支持动作：`publish`(0→1)、`open`(1→2)、`close`(2→1)、`start`(1|2→3)、`finish`(3→4)。非法流转 400。

### 3.6 创建对局 `POST /api/tournaments/{id}/schedules`

```json
{
  "phase_id": 1, "round": 1, "round_name": "小组赛",
  "bo": 3, "is_final": false,
  "home_team_id": 1, "away_team_id": 2,
  "start_time": null
}
```

### 3.7 问数 Agent `POST /api/query`（SSE）

请求：
```json
{ "query": "现在最火爆的比赛是哪个，有多少队伍报名了？" }
```
响应：`text/event-stream`，逐帧 `data: {json}\n\n`：
- 进度事件：`{"type":"progress","step":"召回字段信息","status":"success","message":"..."}`
- 最终事件：`{"type":"done","result":{"columns":[...],"rows":[...]},"sql":"...","error":null}`

步骤枚举：`抽取关键词 / 召回字段信息 / 召回指标信息 / 召回字段取值 / 合并召回信息 / 过滤表信息 / 过滤指标信息 / 补充上下文 / 生成SQL / 校验SQL / 执行查询 / 修正SQL`。

### 3.8 预制提示词 `GET /api/query/presets`

响应 200：`[{"id":"g1","title":"什么比赛最火？","template":"...","params":[...]}]`，按「登录态+角色」服务端过滤（未登录仅 guest 4 条）。

## 四、问数 Agent 权限矩阵（`conf/app_config.yaml`）

| 角色 | 可见表域 | 行级范围 | 备注 |
|---|---|---|---|
| guest | tournament/team/schedule | published | 禁查 player/app_user |
| player | 全表（D1–D5） | published | phone/guid 敏感列仅本人 |
| organizer | 全表 | own_plus_published | 明细强制 `created_by=uid` |
| operator / super_admin | 全表 | all | 敏感列非超管仅本人 |

- 敏感列：`app_user.phone`、`app_user.guid`（非超管必须限定本人）
- 禁止列：`app_user.password_hash`（任何 SQL 出现即拒绝）

## 五、实体字段速查

| 表 | 关键字段 |
|---|---|
| `app_user` | id, nickname, phone, guid, role, password_hash(禁止), created_at |
| `tournament` | id, name, game, team_mode, status, created_by, max_teams, ... |
| `tournament_phase` | id, tournament_id, name, start_time, end_time, status |
| `team` | id, tournament_id, name, status, created_by |
| `player` | id, team_id, user_id, nickname, is_captain, status(AGREED/PENDING/REJECTED) |
| `schedule` | id, tournament_id, phase_id, round, bo, home/away_team_id, home/away_score, status |
