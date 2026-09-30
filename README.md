# 赛事管理 Agent（Tournament Agent）

用户用自然语言查询赛事数据（赛程、比分、积分、统计），后端经 LangGraph 工作流自动生成并执行 SQL，前端以 SSE 流式展示执行步骤与结果表格。

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | React + Vite + TypeScript + TailwindCSS v4 + lucide-react |
| 后端 | FastAPI + LangGraph + langchain |
| 数据访问 | SQLAlchemy 2.0 (async, asyncmy) |
| 知识库 | MySQL(meta 元数据 / dw 事实数据) + Qdrant(字段/指标向量) + Elasticsearch(取值字典) |
| 配置 | OmegaConf + python-dotenv + loguru + jieba |

## 架构

```
前端 (React) 聊天式问数 + SSE 步骤展示 + 结果表格
      │ POST /api/query (SSE)
后端 (FastAPI)
  Router → Service → LangGraph 工作流
  节点链：提取关键词 → 三路并行召回（字段/指标/取值）→ 合并 → 双路过滤（表/指标）
        → 补上下文 → 生成 SQL → EXPLAIN 校验 →(修正/执行)→ 结束
      │
Repository 层
  MySQL(meta)  MySQL(dw)  Qdrant  Elasticsearch
```

## 目录结构

```
├── main.py                        # FastAPI 入口
├── conf/app_config.yaml           # 全局配置
├── prompts/                       # LLM Prompt 模板
├── docker/                        # MySQL / Elasticsearch / Qdrant 基础设施
├── app/
│   ├── conf/                      # 配置加载
│   ├── clients/                   # 4 个客户端管理器（MySQL/Qdrant/ES/Embedding）
│   ├── entities/                  # 纯业务实体（Column/Metric/Value/Tournament/Team/Match）
│   ├── models/                    # SQLAlchemy ORM 映射
│   ├── repositories/              # Repository 层（meta/dw MySQL + Qdrant + ES）
│   ├── agent/
│   │   ├── llm.py                 # LLM 单例
│   │   ├── state.py / context.py  # State（业务数据） / Context（依赖注入）
│   │   ├── graph.py               # LangGraph 图定义（12 节点）
│   │   └── nodes/                 # 12 个图节点
│   ├── services/                  # QueryService：图编排 + SSE / MetaKnowledgeService：知识库构建编排
│   ├── api/                       # lifespan / dependencies / router / schema
│   ├── prompt/                    # Prompt 加载器
│   └── scripts/                   # 脚本入口（只做参数解析与调度：seed / build）
└── frontend/                      # React 聊天界面
```

## 启动步骤

```bash
# 0. 准备环境变量
cp .env.example .env   # 填入 LLM_API_KEY（SiliconFlow）

# 1. 基础设施（MySQL / ES / Qdrant）
cd docker && docker-compose up -d

# 2. 离线构建知识库（首次或元数据变更后）
#    先按 DW 结构生成 conf/meta_config.yaml（可手工修改表/字段/指标定义），
#    再按配置灌入 meta 元数据，最后构建 Qdrant/ES 索引：
cd .. && uv run python -m app.scripts.seed_meta_knowledge --init   # 生成配置（可选，改完表结构后重跑）
uv run python -m app.scripts.seed_meta_knowledge                   # 按配置灌 meta（DW → meta）
uv run python -m app.scripts.build_meta_knowledge                  # 构建 Qdrant/ES 索引

# 3. 启动后端
uv run uvicorn main:app --reload      # http://localhost:8000  （/health、/api/query）

# 4. 启动前端
cd frontend && pnpm dev                # http://localhost:5173
```

## 工作流（LangGraph，12 节点，对应 docs/ag.md）

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

- `app/entities`：业务实体层，统一表示表、字段、指标和值
- `app/models`：ORM 模型层，定义元数据库表对应的 SQLAlchemy 模型
- `app/repositories`：存储访问层，负责与底层存储（MySQL/Qdrant/ES）打交道
- `app/services`：业务编排层，组织完整构建/查询流程（MetaKnowledgeService / QueryService）
- `app/scripts`：脚本入口层，接收参数并启动流程
- `app/conf`：程序内配置结构与配置加载（app_config.yaml / meta_config.yaml）

