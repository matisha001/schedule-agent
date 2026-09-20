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
  节点链：提取关键词 → 多路召回 → 生成 SQL → 校验 →(修正/执行)→ 结束
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
│   │   ├── graph.py               # LangGraph 图定义
│   │   └── nodes/                 # 6 个图节点
│   ├── services/                  # QueryService：图编排 + SSE
│   ├── api/                       # lifespan / dependencies / router / schema
│   ├── prompt/                    # Prompt 加载器
│   └── scripts/                   # 离线知识库构建脚本
└── frontend/                      # React 聊天界面
```

## 启动步骤

```bash
# 0. 准备环境变量
cp .env.example .env   # 填入 LLM_API_KEY（SiliconFlow）

# 1. 基础设施（MySQL / ES / Qdrant）
cd docker && docker-compose up -d

# 2. 离线构建知识库（首次或元数据变更后；当前为骨架，领域逻辑待补充）
cd .. && uv run python -m app.scripts.build_meta_knowledge

# 3. 启动后端
uv run uvicorn main:app --reload      # http://localhost:8000  （/health、/api/query）

# 4. 启动前端
cd frontend && pnpm dev                # http://localhost:5173
```

## 工作流（LangGraph）

```
START → extract_keywords → recall → generate_sql → validate_sql
                                                    │ 通过
                                                    ▼
                                               run_sql → END
                                                    ▲
                              正确 ← validate_sql 失败 → correct_sql ──┘
```

