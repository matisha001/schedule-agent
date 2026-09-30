# LangGraph 问数工作流完整流程

> 本文档记录 `app/agent/graph.py` 的完整图定义、节点职责、状态流转和运行配置。

---

## 一、图结构总览

```
START
  │
  ▼
extract_keywords（jieba 抽取关键词）
  │
  ├──────────────┬──────────────┐
  ▼              ▼              ▼
recall_column  recall_value  recall_metric    ← 三路并行召回
(Qdrant 向量)   (ES 全文)      (Qdrant 向量)
  │              │              │
  └──────────────┴──────────────┘
  │
  ▼
merge_retrieved_info（合并三路结果 + meta MySQL 补全）
  │
  ├──────────────┐
  ▼              ▼
filter_table   filter_metric                   ← 两路并行过滤
(LLM 筛表)      (LLM 筛指标)
  │              │
  └──────────────┘
  │
  ▼
add_extra_context（日期信息 + 数据库方言/版本）
  │
  ▼
generate_sql（LLM 生成 SQL）
  │
  ▼
validate_sql（DW MySQL EXPLAIN 校验）
  │
  ├── error is None ──→ run_sql ──→ END
  │
  └── error != None ──→ correct_sql ──→ run_sql ──→ END
```

---

## 二、节点详情

### 节点 1：extract_keywords

| 项 | 内容 |
|----|------|
| **职责** | 从用户问题中抽取检索关键词 |
| **输入 state** | `query` |
| **输出 state** | `keywords` |
| **外部依赖** | 无（纯本地 jieba） |
| **实现** | `jieba.analyse.extract_tags(query, allowPOS=...)`，按词性过滤，保留名词/地名/英文/动词等 |
| **特殊** | 把原始问题本身也加入关键词列表做兜底 |

### 节点 2：recall_column（并行）

| 项 | 内容 |
|----|------|
| **职责** | 语义召回候选字段 |
| **输入 state** | `query`, `keywords` |
| **输出 state** | `retrieved_column_infos` |
| **外部依赖** | `embedding_client`（向量化）、`column_qdrant_repository`（Qdrant 检索） |
| **流程** | LLM 扩展关键词 → 合并去重 → **批量 Embedding（1 次 API 调用）** → 逐个向量查 Qdrant → 按 column_id 去重 |

### 节点 3：recall_value（并行）

| 项 | 内容 |
|----|------|
| **职责** | 全文召回候选字段取值 |
| **输入 state** | `query`, `keywords` |
| **输出 state** | `retrieved_value_infos` |
| **外部依赖** | `value_es_repository`（ES 检索） |
| **流程** | LLM 扩展取值关键词 → 合并去重 → 逐个关键词查 ES → 按 value_id 去重 |
| **注意** | 不走 Embedding，直接用 ES 全文匹配 |

### 节点 4：recall_metric（并行）

| 项 | 内容 |
|----|------|
| **职责** | 语义召回候选指标 |
| **输入 state** | `query`, `keywords` |
| **输出 state** | `retrieved_metric_infos` |
| **外部依赖** | `embedding_client`、`metric_qdrant_repository` |
| **流程** | LLM 扩展指标关键词 → 合并去重 → 逐个 `aembed_query` → 查 Qdrant → 按 metric_id 去重 |

### 节点 5：merge_retrieved_info

| 项 | 内容 |
|----|------|
| **职责** | 合并三路召回结果，补全完整上下文 |
| **输入 state** | `retrieved_column_infos`, `retrieved_metric_infos`, `retrieved_value_infos` |
| **输出 state** | `table_infos`, `metric_infos` |
| **外部依赖** | `meta_mysql_repository` |
| **流程** | ① 以 column_id 为 key 合并字段 → ② 补全指标依赖字段 → ③ ES 取值合并回字段 examples → ④ 按表组织 → ⑤ 补主外键 → ⑥ 查 meta MySQL 拿表描述 → ⑦ 生成表结构上下文 |

### 节点 6：filter_table（并行）

| 项 | 内容 |
|----|------|
| **职责** | LLM 筛选出本次问题真正需要的表和字段 |
| **输入 state** | `query`, `table_infos` |
| **输出 state** | `table_infos`（裁剪后） |
| **外部依赖** | `llm` |
| **流程** | table_infos 转 YAML 喂给 LLM → LLM 返回 {表名: [字段名]} → 程序按结果裁剪 |

### 节点 7：filter_metric（并行）

| 项 | 内容 |
|----|------|
| **职责** | LLM 筛选出本次问题真正需要的指标 |
| **输入 state** | `query`, `metric_infos` |
| **输出 state** | `metric_infos`（裁剪后） |
| **外部依赖** | `llm` |
| **流程** | metric_infos 转 YAML 喂给 LLM → LLM 返回指标名列表 → 程序按结果裁剪 |

### 节点 8：add_extra_context

| 项 | 内容 |
|----|------|
| **职责** | 补充 SQL 生成所需的运行环境信息 |
| **输入 state** | 无（只读外部） |
| **输出 state** | `date_info`, `db_info` |
| **外部依赖** | `dw_mysql_repository`（查方言版本） |
| **补充内容** | 当前日期/星期/季度 + 数据库方言/版本（MySQL 8.0） |

### 节点 9：generate_sql

| 项 | 内容 |
|----|------|
| **职责** | LLM 生成候选 SQL |
| **输入 state** | `query`, `table_infos`, `metric_infos`, `date_info`, `db_info` |
| **输出 state** | `sql` |
| **外部依赖** | `llm` |
| **流程** | 所有上下文转 YAML → 喂给 LLM → 输出纯文本 SQL（StrOutputParser） |

### 节点 10：validate_sql

| 项 | 内容 |
|----|------|
| **职责** | 用 DW MySQL EXPLAIN 校验 SQL 语法 |
| **输入 state** | `sql` |
| **输出 state** | `error`（None = 通过，str = 错误信息） |
| **外部依赖** | `dw_mysql_repository` |
| **关键** | 校验失败不抛异常，把错误写入 state，由条件边决定走向 |

### 节点 11：correct_sql（条件分支）

| 项 | 内容 |
|----|------|
| **触发条件** | `state["error"] is not None` |
| **职责** | 根据报错信息修正 SQL |
| **输入 state** | 全部上下文 + `sql` + `error` |
| **输出 state** | `sql`（覆盖为修正后的 SQL） |
| **外部依赖** | `llm` |

### 节点 12：run_sql

| 项 | 内容 |
|----|------|
| **职责** | 在 DW MySQL 执行最终 SQL，返回结果 |
| **输入 state** | `sql` |
| **输出 state** | 无（通过 stream_writer 推送 result） |
| **外部依赖** | `dw_mysql_repository` |

---

## 三、State 字段流转图

```
State 字段              extract   recall×3   merge   filter×2   extra   gen_sql   validate  correct   run_sql
─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
query                   读入
keywords                  ← 写
retrieved_column_infos              ← 写
retrieved_value_infos               ← 写
retrieved_metric_infos              ← 写
table_infos                                   ← 写      ← 覆盖
metric_infos                                  ← 写      ← 覆盖
date_info                                              ← 写
db_info                                                ← 写
sql                                                              ← 写              ← 覆盖
error                                                                       ← 写    (条件分支)
```

---

## 四、Context 外部依赖

```python
class DataAgentContext(TypedDict):
    column_qdrant_repository: ColumnQdrantRepository    # 字段向量检索
    embedding_client: OpenAIEmbeddings                  # 文本向量化（云端 API）
    metric_qdrant_repository: MetricQdrantRepository   # 指标向量检索
    value_es_repository: ValueESRepository              # 字段取值全文检索
    meta_mysql_repository: MetaMySQLRepository         # 元数据补全
    dw_mysql_repository: DWMySQLRepository              # SQL 执行 + 方言查询
```

---

## 五、运行配置

### stream_mode 选项

| 模式 | 说明 | 适用场景 |
|------|------|---------|
| `values` | 每个节点执行后的完整 State 快照 | 调试，看每步状态全貌 |
| `updates` | 每个节点本次更新了哪些字段 | 看增量变更 |
| `messages` | LLM 逐 token 输出 | 流式显示模型思考过程 |
| `custom` | 节点通过 `stream_writer` 主动写出的自定义事件 | **生产模式**，前端进度展示 |
| `debug` | 调试信息 | 排查图执行问题 |

### 生产模式（SSE）

```python
async for chunk in graph.astream(
    input=state,
    context=context,
    stream_mode="custom",   # 只收节点主动 writer 出去的进度/结果
):
    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
```

### 本地调试模式

```bash
# 打印 ASCII 图结构 + 跑完整流程
uv run python -m app.agent.graph
```

```python
# 查看完整 State 快照
async for chunk in graph.astream(
    input=state, context=context, stream_mode="values"
):
    print(chunk)
```

### 自定义进度推送

每个节点内部通过 `runtime.stream_writer` 推送：

```python
writer({"type": "progress", "step": "召回字段信息", "status": "running"})
writer({"type": "progress", "step": "召回字段信息", "status": "success"})
writer({"type": "result", "data": result})
```

---

## 六、条件边逻辑

```python
graph_builder.add_conditional_edges(
    source="validate_sql",
    path=lambda state: "run_sql" if state["error"] is None else "correct_sql",
    path_map={"run_sql": "run_sql", "correct_sql": "correct_sql"},
)
```

- `validate_sql` 执行 `EXPLAIN <sql>`：
  - **成功** → `state["error"] = None` → 走 `run_sql`
  - **失败** → `state["error"] = "错误信息字符串"` → 走 `correct_sql` → 修正后回到 `run_sql`

---

## 七、Prompt 文件对应

| 节点 | Prompt 文件 |
|------|------------|
| recall_column | `extend_keywords_for_column_recall.prompt` |
| recall_value | `extend_keywords_for_value_recall.prompt` |
| recall_metric | `extend_keywords_for_metric_recall.prompt` |
| filter_table | `filter_table_info.prompt` |
| filter_metric | `filter_metric_info.prompt` |
| generate_sql | `generate_sql.prompt` |
| correct_sql | `correct_sql.prompt` |

---

## 八、元数据知识库构建流程（离线脚本）

> 与在线查询的 graph 流程对应，离线构建负责把 DW 数仓中的表结构、字段、指标信息同步到 Meta MySQL + Qdrant + ES，供在线召回使用。

### 8.1 构建总览

```
meta_config.yaml（人工配置）
  │
  ▼
build_meta_knowledge.py（入口：初始化客户端 + 创建仓储）
  │
  ▼
MetaKnowledgeService.build()
  │
  ├── [tables 配置存在] ──────────────────────────────┐
  │   1. _save_tables_to_meta_db()                    │
  │      DW MySQL 查真实字段类型 + 示例值               │
  │      → 写入 Meta MySQL（table_info + column_info） │
  │                                                    │
  │   2. _save_column_info_to_qdrant()               │
  │      每个字段拆成多个语义入口（name/desc/alias）    │
  │      → 批量 Embedding（每批 20 条）               │
  │      → 写入 Qdrant（column collection）            │
  │                                                    │
  │   3. _save_value_info_to_es()                     │
  │      sync=true 的字段查 DW 真实值全集               │
  │      → 写入 ES（value index）                       │
  │                                                    │
  ├── [metrics 配置存在] ────────────────────────────┤
  │   4. _save_metrics_to_meta_db()                   │
  │      指标定义 + 字段依赖关系                        │
  │      → 写入 Meta MySQL（metric_info + column_metric）│
  │                                                    │
  │   5. _save_metrics_to_qdrant()                   │
  │      每个指标拆成多个语义入口（name/desc/alias）    │
  │      → 批量 Embedding（每批 20 条）               │
  │      → 写入 Qdrant（metric collection）             │
  │                                                    │
  └────────────────────────────────────────────────────┘
```

### 8.2 五个构建步骤详解

#### Step 1：_save_tables_to_meta_db（表/字段入 Meta MySQL）

| 项 | 内容 |
|----|------|
| **输入** | `meta_config.tables` |
| **数据来源** | DW MySQL（查 `get_column_types` + `get_column_values`） |
| **写入** | Meta MySQL：`table_info` + `column_info` 两张表 |
| **关键逻辑** | 每个字段 id = `表名.字段名`（如 `fact_order.order_amount`），这个 id 在 Qdrant、ES、Meta MySQL 三处统一复用 |
| **事务** | `session.begin()` 批量写入 |

#### Step 2：_save_column_info_to_qdrant（字段向量索引）

| 项 | 内容 |
|----|------|
| **输入** | `column_infos`（Step 1 产出） |
| **写入** | Qdrant column collection |
| **语义入口** | 每个字段拆成多个向量点：① name ② description ③ 每个 alias |
| **Embedding 策略** | 批量 `aembed_documents`，每批 20 条，减少 API 调用次数 |
| **payload** | 完整 ColumnInfo 序列化存入 payload，检索命中后直接拿回全部信息，无需回查 MySQL |
| **collection 初始化** | `ensure_collection()` 自动创建（embedding_size=1024, Distance.COSINE） |

#### Step 3：_save_value_info_to_es（字段取值全文索引）

| 项 | 内容 |
|----|------|
| **输入** | `meta_config.tables` + `column_infos` |
| **数据来源** | DW MySQL（`get_column_values(table, column, 100000)` 取真实值全集） |
| **写入** | ES value index（`data_agent`） |
| **过滤条件** | 仅 `sync: true` 的字段才同步真实值（主键/外键/技术字段 `sync: false`） |
| **ValueInfo id** | `字段id.值`（如 `dim_region.region_name.华北`） |
| **ES mapping** | `value` 字段用 `ik_max_word` 分词，`column_id` 和 `id` 用 keyword 精确匹配 |

#### Step 4：_save_metrics_to_meta_db（指标入 Meta MySQL）

| 项 | 内容 |
|----|------|
| **输入** | `meta_config.metrics` |
| **写入** | Meta MySQL：`metric_info` + `column_metric` 两张表 |
| **关键逻辑** | MetricInfo 表达"指标是什么"，ColumnMetric 表达"指标依赖哪些字段"，同一事务写入 |

#### Step 5：_save_metrics_to_qdrant（指标向量索引）

| 项 | 内容 |
|----|------|
| **输入** | `metric_infos`（Step 4 产出） |
| **写入** | Qdrant metric collection（与字段 collection 分开） |
| **语义入口** | 每个指标拆成：① name ② description ③ 每个 alias |
| **Embedding 策略** | 同 Step 2，批量 20 条 |

### 8.3 配置文件格式（meta_config.yaml）

```yaml
tables:
  - name: fact_order              # 表名（必须与 DW 中实际表名一致）
    role: fact                     # 表角色：dim（维度表）/ fact（事实表）
    description: 订单事实表，记录订单数量和金额等核心指标。
    columns:
      - name: order_amount         # 字段名（必须与 DW 中实际字段名一致）
        role: measure              # 字段角色：primary_key / foreign_key / dimension / measure
        description: 订单金额。     # 字段业务说明（用于向量化语义入口）
        alias: [销售额, 订单金额, 收入]  # 别名（每个别名都是独立的语义入口）
        sync: false                # 是否同步真实值到 ES（维度字段 true，主键/度量 false）

metrics:
  - name: GMV                      # 指标名
    description: 全称Gross Merchandise Value，表示所有订单的成交金额总和。
    relevant_columns:             # 指标依赖的字段（完整 column_id）
      - fact_order.order_amount
    alias: [成交总额, 订单总额]      # 指标别名
```

### 8.4 运行方式

```bash
# 执行一次完整构建
uv run python -m app.scripts.build_meta_knowledge -c conf/meta_config.yaml
```

入口文件 `build_meta_knowledge.py` 的执行流程：

```
1. argparse 解析 -c 参数 → 拿到配置文件路径
2. 初始化 5 个客户端（meta MySQL / dw MySQL / Qdrant / Embedding / ES）
3. 创建 Repository 对象（meta_repo / dw_repo / column_qdrant_repo / value_es_repo / metric_qdrant_repo）
4. 注入 MetaKnowledgeService，调用 build(config_path)
5. 构建完成后关闭所有客户端连接
```

### 8.5 构建与在线查询的数据流对照

```
离线构建（写入）                    在线查询（读取）
─────────────────                  ─────────────────
Meta MySQL table_info ───────────→ merge_retrieved_info 补全表描述
Meta MySQL column_info ──────────→ merge_retrieved_info 补全字段信息
Meta MySQL metric_info ──────────→ merge_retrieved_info 补全指标信息
Qdrant column collection ────────→ recall_column 向量召回字段
Qdrant metric collection ────────→ recall_metric 向量召回指标
ES value index ──────────────────→ recall_value 全文召回取值
DW MySQL 表结构 ─────────────────→ add_extra_context 查方言版本
DW MySQL 数据 ───────────────────→ run_sql 执行 SQL
```
