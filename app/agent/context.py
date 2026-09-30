"""
赛事问数 Agent 运行上下文

Context 用来保存一次图执行过程中不参与状态合并的外部依赖或配置
本章放入多路召回需要的 Embedding 客户端 Qdrant 仓储和 ES 仓储
召回信息合并阶段还会访问 Meta MySQL，用于按 id 补齐字段和表结构元数据
额外上下文补全阶段会访问 DW MySQL，用于读取数据库方言和版本
这样节点可以通过 runtime.context 复用外部工具，而不需要把连接类对象塞进 State
"""

from typing import TypedDict

from langchain_openai import OpenAIEmbeddings

from app.repositories.es.value_es_repository import ValueESRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository


class TournamentAgentContext(TypedDict):
    """LangGraph Runtime 中传递的上下文对象"""

    # 字段向量仓储，负责根据向量从 Qdrant 检索候选字段
    column_qdrant_repository: ColumnQdrantRepository
    # Embedding 客户端，负责把关键词转换成向量检索所需的 query vector
    embedding_client: OpenAIEmbeddings
    # 指标向量仓储，负责根据向量从 Qdrant 检索候选指标
    metric_qdrant_repository: MetricQdrantRepository
    # 字段取值全文检索仓储，负责从 Elasticsearch 检索真实字段值
    value_es_repository: ValueESRepository
    # 元数据仓储，负责在召回结果合并时补齐字段 表 主外键等结构信息
    meta_mysql_repository: MetaMySQLRepository
    # 数仓仓储，负责在额外上下文补全时读取数据库方言 版本等执行环境信息
    dw_mysql_repository: DWMySQLRepository

    # ---- 问数权限上下文（docs/permission-design.md 第 4/5 节） ----
    # 角色：guest / player / organizer / operator / super_admin
    role: str
    # 当前登录用户 id（未登录为 None）
    user_id: int | None
    # 角色可见表集合（召回裁剪用；空集表示不裁剪）
    allowed_tables: set[str]
    # 完全不可见表集合（guest 的 player/app_user）
    deny_tables: set[str]
    # 敏感列（"表.列"）：非超管引用时必须限定本人
    sensitive_columns: set[str]
    # 禁止列（"表.列"）：任何 SQL 中出现即拒绝
    forbid_columns: set[str]
    # 行级范围：published / own_plus_published / all
    row_scope: str
