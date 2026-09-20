"""LangGraph 上下文定义：外部依赖注入，不随节点合并。"""

from typing import TypedDict

from langchain_openai import OpenAIEmbeddings

from app.repositories.es.value_es_repository import ValueESRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository


class TournamentAgentContext(TypedDict):
    column_qdrant_repository: ColumnQdrantRepository
    embedding_client: OpenAIEmbeddings
    metric_qdrant_repository: MetricQdrantRepository
    value_es_repository: ValueESRepository
    meta_mysql_repository: MetaMySQLRepository
    dw_mysql_repository: DWMySQLRepository
