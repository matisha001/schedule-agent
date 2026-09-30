# 赛事管理 Agent（Tournament Agent）

一个双模块项目：**赛事业务管理系统**（用户认证、赛事配置、报名、赛程/对局管理）+ **自然语言问数 Agent**（LangGraph 工作流自动生成并执行 SQL，SSE 流式展示步骤与结果表格）。

## 功能总览

| 模块 | 能力 |
|---|---|
| 用户认证 | 手机号 + 密码登录（新用户自动注册）、无状态 Token、PBKDF2 密码哈希 |
| 赛事管理 | 赛事 CRUD、基础配置（游戏/地图/人数上限/报名方式/规则）、状态流转（草稿→已发布→报名中→比赛中→已结束） |
| 阶段管理 | 赛事阶段（名称/起止时间/状态）维护 |
| 报名管理 | 队伍 + 选手管理；选手自主报名 / 办赛者代报名；队伍审核、队长指派、选手状态（AGREED/PENDING/REJECTED） |
| 赛程管理 | 对局编排（阶段/轮次/BO/决赛标记）、比分录入、对局状态流转 |
| 问数 Agent | 自然语言查询赛事数据，LangGraph 12 节点工作流：关键词抽取 → 三路并行召回 → 双路过滤 → SQL 生成/校验/修正/执行，SSE 实时推送执行步骤 |
| 前端 | 双入口：官网（玩家视角）+ 管理后台（办赛者视角），React 聊天式问数页 |

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | React 19 + Vite 8 + TypeScript + TailwindCSS v4 + react-router-dom 7 + lucide-react |
| 后端 | FastAPI + LangGraph + langchain |
| 数据访问 | SQLAlchemy 2.0 (async, asyncmy) |
| 业务库 | MySQL 8.0（`schedule_dw`：6 张业务表） |
| 知识库 | MySQL（`schedule_meta`：4 张元数据表）+ Qdrant（字段/指标向量）+ Elasticsearch 8.17 + IK 中文分词（取值字典） |
| LLM | SiliconFlow：DeepSeek-V4-Flash（SQL 生成）+ BAAI/bge-large-zh-v1.5（Embedding） |
| 安全 | HMAC-SHA256 无状态 Token + PBKDF2-HMAC-SHA256 密码哈希（600,000 迭代） |
| 配置 | OmegaConf + python-dotenv + loguru + jieba |

## 系统架构

```
┌───────────────────────── 前端 (React) ─────────────────────────┐
│  官网（玩家）：赛事列表/详情/报名/我的赛事/Ask 问数             │
│  管理后台（办赛者）：赛事管理/基础配置/报名管理/赛程管理        │
└──────────────┬──────────────────────────────┬──────────────────┘
               │ REST（业务接口）              │ POST /api/query (SSE)
               ▼                              ▼
┌───────────────────────── 后端 (FastAPI) ───────────────────────┐
│  auth_router / tournament_router / registration_router          │
│  schedule_router                               query_router     │
│       │                                            │            │
│  TournamentService（业务编排）                QueryService（图编排）│
│  权限校验/状态机/报名规则                       LangGraph 12 节点 │
│       │                                            │            │
└───────┼────────────────────────────────────────────┼────────────┘
        ▼                                            ▼
┌────────────────────────────────────────────────────────────────┐
│ Repository 层                                                  │
│  MySQL(schedule_dw 业务)  MySQL(schedule_meta 元数据)           │
│  Qdrant(字段/指标向量)  Elasticsearch(取值字典)                 │
└────────────────────────────────────────────────────────────────┘
```

## 数据模型

### 业务库 schedule_dw（6 张表）

```
app_user（用户） ──1:N── tournament（赛事） ──1:N── tournament_phase（阶段）
                                │
                                ├─1:N── team（队伍） ──1:N── player（选手，user_id→app_user）
                                └─1:N── schedule（对局，home/away_team_id→team）
```

| 表 | 说明 | 关键状态枚举 |
|---|---|---|
| `app_user` | 登录用户/主办方（id=1 为系统虚拟用户） | — |
| `tournament` | 赛事主表：名称/游戏/地图/人数上限/报名方式/规则 | status：0草稿 1已发布 2报名中 3比赛中 4已结束 |
| `tournament_phase` | 赛事阶段（仅存名称/时间/状态） | status：0未开始 1进行中 2已结束 |
| `team` | 报名队伍 | status：0待审核 1已确认 2已驳回 3已取消 |
| `player` | 选手（TEMP 临时选手 user_id 可空） | status：AGREED / PENDING / REJECTED |
| `schedule` | 对局/赛程（BO 总比分） | status：0未开赛 1进行中 2已结束 3已取消 |

赛事状态流转：`publish(0→1) → open(1→2) → close(2→1) / start(1|2→3) → finish(3→4)`，非法流转由服务层拦截。

### 知识库 schedule_meta（4 张表，供问数 Agent 用）

`table_info`（表元数据）/ `column_info`（字段元数据，含别名/示例值）/ `metric_info`（指标）/ `value_info`（字段取值字典）

完整字段设计见 `docs/table-design.md`（V4 定稿）。

## 认证与安全

- **登录**：`POST /api/auth/login`（手机号 + 密码）。新手机号自动注册（昵称默认 `玩家{尾号4位}`）；历史无密码用户首次登录自动设置密码完成认领；密码错误统一返回"手机号或密码错误"，不泄露账号存在性。
- **Token**：HMAC-SHA256 签名的无状态 Token（`base64url(payload).base64url(signature)`，payload 为 `{uid, exp}`），默认有效期 7 天，密钥来自 `TOKEN_SECRET`。
- **密码哈希**：标准库 PBKDF2-HMAC-SHA256（600,000 迭代，随机盐），未引入 bcrypt/passlib（Python 3.14 兼容性考虑）。

## API 一览

| 模块 | 方法 & 路径 | 说明 |
|---|---|---|
| Health | `GET /health` | 健康检查 |
| Auth | `POST /api/auth/login` | 手机号+密码登录（自动注册） |
| Auth | `GET /api/auth/me` | 当前用户信息 |
| Tournament | `GET/POST /api/tournaments` | 赛事列表（`scope=published\|mine`）/ 创建 |
| Tournament | `GET/PUT/DELETE /api/tournaments/{id}` | 赛事详情 / 更新 / 删除 |
| Tournament | `POST /api/tournaments/{id}/transition` | 赛事状态流转（publish/open/close/start/finish） |
| Tournament | `GET/POST /api/tournaments/{id}/phases` | 阶段列表 / 创建 |
| Tournament | `PUT/DELETE /api/tournaments/phases/{phase_id}` | 阶段更新 / 删除 |
| Registration | `GET /api/me/tournaments` | 我报名的赛事 |
| Registration | `GET/POST /api/tournaments/{id}/teams` | 队伍列表 / 自主报名 |
| Registration | `POST /api/tournaments/{id}/admin-teams` | 办赛者代报名 |
| Registration | `PATCH /api/teams/{id}/status`、`DELETE` | 队伍审核 / 删除 |
| Registration | `POST /api/teams/{id}/players` | 添加选手 |
| Registration | `PATCH /api/players/{id}/captain`、`/status`、`DELETE` | 队长指派 / 选手状态 / 删除 |
| Schedule | `GET/POST /api/tournaments/{id}/schedules` | 对局列表 / 创建 |
| Schedule | `PATCH/DELETE /api/schedules/{id}` | 对局更新（含比分）/ 删除 |
| Query | `POST /api/query` | Agent 问数（SSE 事件流） |

## 前端页面

```
/login                          登录（手机号 + 密码）
官网（玩家视角）  /
  /                             赛事列表（已发布）
  /tournaments/:id              赛事详情（阶段/队伍/赛程，登录后显示报名入口）
  /register/:id                 报名链接直达（自动打开报名弹窗）
  /my                           我的赛事（需登录）
  /ask                          Ask 问数页（SSE 流式展示 Agent 执行步骤 + 结果表格）
管理后台（办赛者视角）  /admin
  /admin                        我的赛事管理列表
  /admin/tournaments/:id        赛事管理详情（基础配置 / 报名管理 / 赛程管理 三个 Tab）
```

## 目录结构

```
├── main.py                        # FastAPI 入口（挂载 5 个 router）
├── conf/
│   ├── app_config.yaml            # 全局配置（双库/Qdrant/ES/LLM/auth）
│   └── meta_config.yaml           # 知识库元数据配置（表/字段/指标/取值定义）
├── prompts/                       # LLM Prompt 模板（7 个：关键词扩展/过滤/SQL 生成/修正）
├── docker/                        # 基础设施
│   ├── docker-compose.yaml        # MySQL 8.0 / ES 8.17(IK) / Qdrant
│   ├── mysql/                     # init.sql + schema_meta.sql + schema_dw.sql
│   └── elasticsearch/Dockerfile   # 单节点 ES + IK 中文分词插件
├── docs/
│   ├── ag.md                      # LangGraph 工作流完整文档（12 节点）
│   ├── domain-overview.md         # 领域模型说明（接口样例 → 实体映射）
│   └── table-design.md            # 表结构设计（V4 定稿，含 ER 图）
├── app/
│   ├── conf/                      # 配置加载（app_config / meta_config）
│   ├── core/                      # 通用工具：idgen（雪花ID）/ security（Token）/ log
│   ├── clients/                   # 4 个客户端管理器（MySQL 管理 meta/dw 双连接 + Qdrant/ES/Embedding）
│   ├── entities/                  # 纯业务实体（User/Tournament/Team/Player/Schedule/...）
│   ├── models/                    # SQLAlchemy ORM 映射（meta + dw）
│   ├── repositories/              # Repository 层（meta/dw MySQL + Qdrant + ES + mappers）
│   ├── agent/
│   │   ├── llm.py                 # LLM 单例
│   │   ├── state.py / context.py  # State（业务数据） / Context（依赖注入）
│   │   ├── graph.py               # LangGraph 图定义（12 节点）
│   │   └── nodes/                 # 12 个图节点
│   ├── services/                  # TournamentService（业务编排）/ QueryService（SSE 图编排）
│   │                              # MetaKnowledgeService（知识库构建编排）/ security（密码哈希）
│   ├── api/                       # lifespan / dependencies / schemas / 5 个 router
│   ├── prompt/                    # Prompt 加载器
│   └── scripts/                   # 脚本入口（seed / build）
└── frontend/                      # React 应用（官网 + 管理后台 + Ask）
```

## 问数 Agent 工作流（LangGraph，12 节点，对应 docs/ag.md）

```
START → extract_keywords
        ├─→ recall_column（Qdrant 字段向量）
        ├─→ recall_value（ES 取值字典全文）       三路并行
        └─→ recall_metric（Qdrant 指标向量）
              ↓
        merge_retrieved_info（按字段/表组织，补主外键与表描述）
        ├─→ filter_table（LLM 裁剪候选表与字段）  双路并行
        └─→ filter_metric（LLM 裁剪候选指标）
              ↓
        add_extra_context（日期 + 数据库信息）
              ↓
        generate_sql → validate_sql（只读正则防线 + EXPLAIN）
                        │ error 为空（校验通过）
                        ▼
                      run_sql → END（结果写回 state.result，SSE done 事件）
                        ▲
        correct_sql ←──┘ error 非空（修正后重入 run_sql）
```

## 代码分层

```
scripts（入口/调度） → services（业务编排） → repositories（存储读写） → mappers（对象转换） → models（ORM）↔ 数据库
                                                          ↘ entities（业务实体，与 ORM 模型分离）
```

- `app/entities`：业务实体层，统一表示表、字段、指标和值（与 ORM 模型解耦）
- `app/models`：ORM 模型层，定义 meta / dw 库对应的 SQLAlchemy 模型
- `app/repositories`：存储访问层，负责与底层存储（MySQL/Qdrant/ES）打交道
- `app/services`：业务编排层（TournamentService / QueryService / MetaKnowledgeService）
- `app/scripts`：脚本入口层，只做参数解析与调度（seed / build）
- `app/conf`：程序内配置结构与配置加载（app_config.yaml / meta_config.yaml）

## 启动步骤

```bash
# 0. 准备环境变量
cp .env.example .env   # 填入 LLM_API_KEY（SiliconFlow），可选 TOKEN_SECRET（生产必填）

# 1. 基础设施（MySQL / ES / Qdrant）
cd docker && docker-compose up -d

# 2. 初始化业务库 + 灌入知识库元数据（首次或元数据变更后）
#    业务表 DDL 由 docker/mysql/schema_dw.sql 自动执行（docker-entrypoint-initdb.d）；
#    知识库侧先按 DW 结构生成 conf/meta_config.yaml（可手工修改表/字段/指标定义），
#    再按配置灌入 meta 元数据，最后构建 Qdrant/ES 索引：
cd .. && uv run python -m app.scripts.seed_meta_knowledge --init   # 生成配置（可选，改完表结构后重跑）
uv run python -m app.scripts.seed_meta_knowledge                   # 按配置灌 meta（DW → meta）
uv run python -m app.scripts.build_meta_knowledge                  # 构建 Qdrant/ES 索引

# 3. 启动后端
uv run uvicorn main:app --reload      # http://localhost:8000  （/health、/api/*）

# 4. 启动前端
cd frontend && pnpm dev                # http://localhost:5173
# 可选：如需跨域/联调，设置 VITE_API_BASE_URL（如 http://localhost:8000）
```

## 文档索引

| 文档 | 内容 |
|---|---|
| `docs/ag.md` | LangGraph 问数工作流完整说明（图定义、12 节点职责、状态流转、运行配置） |
| `docs/domain-overview.md` | 领域模型说明（接口样例 → 实体映射、敏感信息脱敏约定） |
| `docs/table-design.md` | 表结构设计 V4（字段明细、ER 图、状态枚举、最小流程流转） |
