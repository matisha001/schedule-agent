# 赛事问数助手 · 权限管理设计（定稿）

> 状态：定稿待实施 ｜ 关联模块：用户认证 / 问数 Agent（LangGraph 12 节点）/ 管理后台
> 决策来源：2026-09-30 用户拍板（不强制登录、超管引导创建、敏感字段仅本人、办赛者 自己+已发布）

## 1. 目标

1. 引入角色体系（超管/运营/办赛者/玩家/游客），支持页面化用户权限管理。
2. 问数助手不强制登录：未登录用户（游客）仅可查询公开信息。
3. 预制提示词按「登录态 + 角色」服务端过滤，每种角色默认 4 条，以"比赛情况分析"为核心。
4. 敏感字段（手机号/guid）仅允许当前用户查询自己的；办赛者只能查询自己创办的比赛下的用户信息。
5. 权限强制链路不依赖 LLM 自觉：召回裁剪 → 生成约束 → 确定性终检三层防线。

## 2. 角色体系

| 角色 | 标识 | 来源 | 问数范围 | 系统能力 |
|---|---|---|---|---|
| 系统超管 | `super_admin` | 首次启动引导创建（1~N 人） | 全部数据域含敏感字段 | 全部 + 用户/权限管理页 |
| 运营 | `operator` | 超管在用户管理页指派 | 全部赛事数据，敏感字段仅本人 | 平台级问数 |
| 办赛者 | `organizer` | 超管指派（默认创建赛事即可管理自己的赛事） | 自己创办的赛事 + 全部已发布；选手/队伍/用户信息仅限自己赛事 | 自己的赛事管理（现状能力） |
| 玩家 | `player` | 注册默认（`app_user.role` 默认值） | 已发布赛事公开数据 + 自己的敏感信息 | 报名/我的赛事 |
| 游客 | `guest` | 未登录（不落库） | 已发布赛事的公开数据（不含选手/用户表） | 浏览官网 + 公开问数 |

存储：`app_user.role VARCHAR(16) NOT NULL DEFAULT 'player'`。

## 3. 问数功能域（权限矩阵）

| 功能域 | 表 | 游客 guest | 玩家 player | 办赛者 organizer | 运营 operator | 超管 super_admin |
|---|---|---|---|---|---|---|
| D1 赛事信息 | tournament | ✅ 仅已发布 | ✅ 仅已发布 | ✅ 自己+已发布 | ✅ 全部 | ✅ 全部 |
| D2 报名队伍 | team | ✅ 仅已确认 | ✅ 仅已发布 | ✅ 自己+已发布 | ✅ 全部 | ✅ 全部 |
| D3 选手信息 | player | ❌ | ✅ 仅已发布 | ✅ 仅自己赛事 | ✅ 全部 | ✅ 全部 |
| D4 赛程比分 | schedule | ✅ 仅已发布 | ✅ 仅已发布 | ✅ 自己+已发布 | ✅ 全部 | ✅ 全部 |
| D5 敏感信息 | app_user(phone/guid) | ❌ | ✅ 仅本人 | ✅ 仅本人 | ✅ 仅本人 | ✅ 全部 |
| M 指标聚合 | 7 个预定义指标 | ✅ 公开口径 | ✅ 公开口径 | ✅ 自己+公开 | ✅ 全部 | ✅ 全部 |

说明：
- 行级范围会套用到指标 SQL 上（如游客统计"参赛人数"仅统计已发布赛事）。
- 游客可查聚合（M）但不可查明细（D3/D5）：聚合脱敏设计。

## 4. 行级注入规则（确定性执行，validate_sql 检查 + correct_sql 修正闭环）

| 角色 | 行级强制 |
|---|---|
| guest | SQL 含 tournament → 必须含 `status >= 1` 约束；出现 player/app_user 表 → 拒绝 |
| player | 公开查询含 tournament → 必须含 `status >= 1`；SQL 引用 phone/guid → 必须含 `app_user.id = {uid}` |
| organizer | 公开查询含 tournament → 必须含 `status >= 1`；涉 player/team/schedule 明细 → 必须含 `tournament.created_by = {uid}` 且 SQL 中必须有 tournament 表 |
| operator | 无赛事行级限制；SQL 引用 phone/guid → 必须含 `app_user.id = {uid}` |
| super_admin | 无限制 |

规则实现要点：
- 检查规则用正则做**确定性匹配**（表名白名单 + 行级条件），不依赖 LLM。
- 生成/修正阶段 prompt 注入行级约束说明；校验失败的错误信息携带"需要补充的条件"，交给 `correct_sql` 修正。
- **禁止列**：`app_user.password_hash` 出现在任何 SQL 中一律拒绝（非超管）。
- 表集合检查：涉 D3/D5 明细且非超管时，SQL 必须显式 join `tournament` 表，否则拒绝。

## 5. 问数三层防线

```
入口(可选登录,取角色) → ①召回裁剪 → ②生成约束 → ③validate_sql 确定性终检 → 只读执行
```

| 防线 | 位置 | 机制 |
|---|---|---|
| ① 召回裁剪 | recall_column / recall_value / recall_metric | guest 剔除 player/app_user 表；非超管剔除不在域白名单内的表；敏感列保留但由③兜底（"我的手机号"需要召回） |
| ② 生成约束 | filter_table / filter_metric / generate_sql / correct_sql | 候选已在①裁剪；prompt 注入角色 + 行级约束说明（必须带 WHERE） |
| ③ 确定性终检 | validate_sql | 表名 ⊆ 白名单、禁止列拦截、行级条件正则校验（缺失 → error → correct_sql 修正） |

## 6. 超管首次启动引导创建

```
lifespan 启动 → 查询 app_user 是否存在 role='super_admin'
  无 → 生成一次性初始化码（随机6位，打印日志；GET /api/auth/bootstrap/status 返回）
登录页检测 need_bootstrap=true → 显示"系统初始化"入口
输入 初始化码 + 手机号 + 密码 → POST /api/auth/bootstrap
  事务内二次校验"仍无超管" → 创建 role='super_admin' 用户（幂等、防抢注）
已有超管后 bootstrap 接口自动关闭；PATCH role 保护最后一名超管不可降级
```

## 7. 预制提示词（preset_queries.yaml，服务端按角色过滤）

- 配置：`conf/preset_queries.yaml`；接口：`GET /api/query/presets`（可选登录，未登录=guest）
- 每种角色默认恰好 4 条；点击后与手输等价，走完整三层防线
- 参数模板（`{赛事名}`）：前端弹赛事选择器（已发布 + 办赛者自己的赛事），选中后拼完整 query

### guest（游客，公开数据分析）
| 标题 | 模板 |
|---|---|
| 什么比赛最火？ | 现在最火爆的比赛是哪个，有多少队伍报名了？ |
| 哪场打得最激烈？ | 哪场比赛的比分最高、打得最激烈？ |
| 现在有哪些比赛可以看？ | 现在有哪些比赛正在报名或进行中？ |
| 最近战况如何？ | 最近打完的比赛里，哪场得分最高？ |

### player（玩家，我的比赛分析）
| 标题 | 模板 |
|---|---|
| 我的比赛概览 | 我报名参加的比赛有哪些，各自是什么状态？ |
| 我的近三场比赛分析 | 我最近参加的 3 场比赛分别是什么赛事、我所在队伍、对局和比分？ |
| 我的队伍分析 | 我所在队伍的状态和成员组成？ |
| 我的手机号 | 我的手机号是多少？ |

### organizer（办赛者，赛事运营分析，涉选手/队伍/用户域强制 created_by=uid）
| 标题 | 模板 |
|---|---|
| 我的赛事报名分析 | 我举办的比赛各自的报名队伍数、选手数、队伍状态分布？ |
| 某场比赛报名分析 | {赛事名} 的报名情况：队伍、选手、待审核数量？ |
| 某场比赛赛程分析 | {赛事名} 的赛程进展：各阶段对局完成情况、比分最高场？ |
| 某场比赛选手信息 | {赛事名} 的参赛选手有哪些？ |

### operator（运营，平台分析）
| 标题 | 模板 |
|---|---|
| 平台赛事汇总 | 全部比赛的报名、赛程、比分汇总统计？ |
| 平台报名排行 | 报名队伍数最多的 10 个比赛有哪些？ |
| 平台赛程分析 | 全部比赛的赛程完成进度如何？ |
| 注册用户数 | 平台注册用户有多少？ |

### super_admin（超管，平台 + 用户全量分析）
| 标题 | 模板 |
|---|---|
| 平台赛事汇总 | 全部比赛的报名、赛程、比分汇总统计？ |
| 注册用户数 | 平台注册用户有多少？ |
| 用户角色分布 | 各角色用户数量分布是怎么样的？ |
| 全量报名分析 | 全部比赛的报名队伍与选手统计？ |

## 8. 配置结构

### conf/app_config.yaml 新增段（权限矩阵）

```yaml
query_permissions:
  domains:
    D1: { tables: [tournament] }
    D2: { tables: [team] }
    D3: { tables: [player] }
    D4: { tables: [schedule] }
    D5: { tables: [app_user] }
  roles:
    guest:        { domains: [D1, D2, D4, M], row_scope: published, deny_tables: [player, app_user] }
    player:       { domains: [D1, D2, D3, D4, M], row_scope: published }
    organizer:    { domains: [D1, D2, D3, D4, M], row_scope: own_plus_published }
    operator:     { domains: [D1, D2, D3, D4, M], row_scope: all }
    super_admin:  { domains: [D1, D2, D3, D4, D5, M], row_scope: all }
  sensitive_columns: ["app_user.phone", "app_user.guid", "app_user.password_hash"]
  forbid_columns:    ["app_user.password_hash"]
```

### conf/preset_queries.yaml（预制提示词）

```yaml
preset_queries:
  - id: g1
    title: 什么比赛最火？
    template: 现在最火爆的比赛是哪个，有多少队伍报名了？
    visible_to: [guest, player, organizer, operator, super_admin]
    order: 1
  # ...（完整 20 条见第 7 节，order 1-4）
```

## 9. 改动清单

### 数据层
- `docker/mysql/schema_dw.sql`：`app_user` 增加 `role` 列（新部署生效）
- `app/scripts/migrate_role.py`：幂等迁移脚本（已存在库 `ALTER TABLE` 补列）

### 后端
- `app/models/app_user_info.py` / `app/entities/app_user_info.py` / mappers：增加 `role`
- `app/api/dependencies.py`：`require_role()`；`get_optional_user` 保留
- `app/api/routers/auth_router.py`：`me` 返回 `role`；新增 `GET /api/auth/bootstrap/status`、`POST /api/auth/bootstrap`
- `app/api/routers/admin_router.py`：`GET /api/admin/users`、`PATCH /api/admin/users/{id}/role`（保护最后超管）
- `app/api/routers/query_router.py`：可选登录取角色；新增 `GET /api/query/presets`
- `app/agent/state.py` / `context.py`：Context 增加 role/user_id/allowed_tables/sensitive_columns/forbid_columns
- `app/services/query_service.py`：`query(query, user)` 构造权限上下文
- 节点：`recall_column/recall_value`（裁剪）、`filter_table/filter_metric`（prompt 注入）、`generate_sql/correct_sql`（prompt 注入行级约束）、`validate_sql`（表白名单 + 禁止列 + 行级条件校验）
- `app/core/bootstrap.py`：初始化码生成/校验（lifespan 调用）
- `main.py`：挂载 admin_router

### 前端
- `types.ts`：User.role、PresetQuery、AdminUser
- `lib/auth.tsx`：user 带 role
- `components/RequireRole.tsx`：新增
- `App.tsx` / `Layout.tsx`：`/admin/users` 路由 + 导航（仅超管可见）
- `pages/admin/AdminUsersPage.tsx`：用户列表 + 改角色
- `pages/portal/AskPage.tsx`：预制提示词渲染 + 参数选择器 + 可查范围提示
- `pages/LoginPage.tsx`：bootstrap 状态检测 + 系统初始化入口

## 10. 实施与验证

P0 数据层 → P1 角色体系（后端+前端用户管理）→ P2 问数权限（防线+提示词）→ P3 前端 → 验证。

验证用例（5 角色 × 关键模板 × 行级注入）：
1. 游客：4 条公开提示词可用；请求选手明细被拒；"我的手机号"不可见。
2. 玩家：查"我的手机号"只返回自己；查他人手机号被拒/只回自己。
3. 办赛者：查自己赛事选手 OK；构造跨赛事 SQL（created_by 非本人）被拒。
4. 运营/超管：全量可查；超管可查任意用户手机号；运营查他人手机号被拒。
5. 超管引导：无超管时 bootstrap 流程可创建；创建后接口关闭；最后超管不可降级。
