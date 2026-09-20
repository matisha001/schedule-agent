"""MySQL 异步客户端管理器（meta 元数据库 / dw 赛事数据仓库各一个实例）。"""

import sys
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.conf.app_config import DBConfig, app_config


class MySQLClientManager:
    def __init__(self, config: DBConfig):
        self.engine: AsyncEngine | None = None
        self.session_factory = None
        self.config = config

    def init(self):
        url = (
            f"mysql+asyncmy://{self.config.user}:{self.config.password}"
            f"@{self.config.host}:{self.config.port}/{self.config.database}?charset=utf8mb4"
        )
        self.engine = create_async_engine(url, pool_size=10, pool_pre_ping=True)
        self.session_factory = async_sessionmaker(self.engine, autoflush=True, expire_on_commit=False)

    async def close(self):
        if self.engine is not None:
            await self.engine.dispose()


meta_mysql_client_manager = MySQLClientManager(app_config.db_meta)
dw_mysql_client_manager = MySQLClientManager(app_config.db_dw)
