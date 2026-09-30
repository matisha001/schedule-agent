"""FastAPI lifespan：统一初始化/关闭外部客户端 + 超管引导检测。"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.mysql_client_manager import (
    dw_mysql_client_manager,
    meta_mysql_client_manager,
)
from app.clients.qdrant_client_manager import qdrant_client_manager
from app.core.bootstrap import bootstrap_status
from app.repositories.mysql.dw.dw_mysql_repository import dw_mysql_repository


@asynccontextmanager
async def lifespan(app: FastAPI):
    qdrant_client_manager.init()
    embedding_client_manager.init()
    es_client_manager.init()
    meta_mysql_client_manager.init()
    dw_mysql_client_manager.init()
    # 无超管时打印一次性初始化码（引导创建超管，docs/permission-design.md 第 6 节）
    await bootstrap_status(dw_mysql_repository)
    yield
    await qdrant_client_manager.close()
    await es_client_manager.close()
    await meta_mysql_client_manager.close()
    await dw_mysql_client_manager.close()
