"""FastAPI 依赖注入：组装 QueryService（各 Repository 均为模块级单例）。"""

from app.clients.embedding_client_manager import embedding_client_manager
from app.repositories.es.value_es_repository import value_es_repository
from app.repositories.mysql.dw.dw_mysql_repository import dw_mysql_repository
from app.repositories.mysql.meta.meta_mysql_repository import meta_mysql_repository
from app.repositories.qdrant.column_qdrant_repository import column_qdrant_repository
from app.repositories.qdrant.metric_qdrant_repository import metric_qdrant_repository
from app.services.query_service import QueryService


def get_query_service() -> QueryService:
    return QueryService(
        meta_mysql_repository=meta_mysql_repository,
        embedding_client=embedding_client_manager.client,
        dw_mysql_repository=dw_mysql_repository,
        column_qdrant_repository=column_qdrant_repository,
        metric_qdrant_repository=metric_qdrant_repository,
        value_es_repository=value_es_repository,
    )
