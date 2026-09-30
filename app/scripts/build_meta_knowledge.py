"""
元数据知识库构建脚本入口

相当于构建流程的 controller 层，负责初始化客户端 创建仓储和服务对象
再把真正的构建任务调度到 MetaKnowledgeService，它本身不承载复杂业务细节
主要目标是把整条构建链路稳定地启动起来
"""

import asyncio

from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.mysql_client_manager import (
    dw_mysql_client_manager,
    meta_mysql_client_manager,
)
from app.clients.qdrant_client_manager import qdrant_client_manager
from app.repositories.es.value_es_repository import value_es_repository
from app.repositories.mysql.dw.dw_mysql_repository import dw_mysql_repository
from app.repositories.mysql.meta.meta_mysql_repository import meta_mysql_repository
from app.repositories.qdrant.column_qdrant_repository import column_qdrant_repository
from app.repositories.qdrant.metric_qdrant_repository import metric_qdrant_repository
from app.services.meta_knowledge_service import MetaKnowledgeService


async def build():
    """初始化依赖并执行一次元数据知识构建"""

    # 初始化元数据MySQL客户端
    meta_mysql_client_manager.init()
    # 初始化数据仓库MySQL客户端
    dw_mysql_client_manager.init()
    # 初始化Qdrant客户端
    qdrant_client_manager.init()
    # 初始化Embedding客户端
    embedding_client_manager.init()
    # 初始化Elasticsearch客户端
    es_client_manager.init()

    # 仓储层在 client manager 内部维护连接池，直接复用模块级单例
    meta_knowledge_service = MetaKnowledgeService(
        meta_mysql_repository=meta_mysql_repository,
        dw_mysql_repository=dw_mysql_repository,
        column_qdrant_repository=column_qdrant_repository,
        metric_qdrant_repository=metric_qdrant_repository,
        value_es_repository=value_es_repository,
        embedding_client=embedding_client_manager.client,
    )

    # 真正进入服务层的构建逻辑：字段/指标向量索引 + 字段取值全文索引
    await meta_knowledge_service.build()

    # 结束后关闭客户端连接
    await meta_mysql_client_manager.close()
    await dw_mysql_client_manager.close()
    await qdrant_client_manager.close()
    await es_client_manager.close()


if __name__ == "__main__":
    asyncio.run(build())
