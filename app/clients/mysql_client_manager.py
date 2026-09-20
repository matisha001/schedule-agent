"""MySQL 异步客户端管理器（meta 元数据库 / dw 赛事数据仓库各一个实例）。

注意：部分机器 /etc/hosts 缺少 localhost 映射（如 SwitchHosts 接管），
asyncmy 会报 nodename nor servname；此处把 localhost 解析为 127.0.0.1，
配置文件仍可填写 localhost。
"""

import sys
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.conf.app_config import DBConfig, app_config


def _resolve_host(host: str) -> str:
    """驱动层兼容：localhost → 127.0.0.1。"""
    return "127.0.0.1" if host == "localhost" else host


class MySQLClientManager:
    def __init__(self, config: DBConfig):
        self.engine: AsyncEngine | None = None
        self.session_factory = None
        self.config = config

    def init(self):
        url = (
            f"mysql+asyncmy://{self.config.user}:{self.config.password}"
            f"@{_resolve_host(self.config.host)}:{self.config.port}/{self.config.database}?charset=utf8mb4"
        )
        # 注意：asyncmy 与 pool_pre_ping 不兼容（连接复用时 MissingGreenlet），
        # 改用 pool_recycle 定期回收连接，避免 MySQL wait_timeout 后的过期连接。
        self.engine = create_async_engine(
            url,
            pool_size=10,
            pool_pre_ping=False,
            pool_recycle=3600,
        )
        self.session_factory = async_sessionmaker(self.engine, autoflush=True, expire_on_commit=False)

    async def close(self):
        if self.engine is not None:
            await self.engine.dispose()


meta_mysql_client_manager = MySQLClientManager(app_config.db_meta)
dw_mysql_client_manager = MySQLClientManager(app_config.db_dw)
