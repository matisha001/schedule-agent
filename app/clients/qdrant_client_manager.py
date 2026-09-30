"""Qdrant 向量库客户端管理器（存字段/赛事术语等知识向量）。

注意：部分机器 /etc/hosts 缺少 localhost 映射（如 SwitchHosts 接管），
驱动层会报 nodename nor servname；此处把 localhost 解析为 127.0.0.1。
"""

import sys
from pathlib import Path

from qdrant_client import AsyncQdrantClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.conf.app_config import QdrantConfig, app_config


def _resolve_host(host: str) -> str:
    """驱动层兼容：localhost → 127.0.0.1。"""
    return "127.0.0.1" if host == "localhost" else host


class QdrantClientManager:
    def __init__(self, config: QdrantConfig):
        self.client: AsyncQdrantClient | None = None
        self.config = config

    def init(self):
        self.client = AsyncQdrantClient(
            url=f"http://{_resolve_host(self.config.host)}:{self.config.port}"
        )

    async def close(self):
        if self.client is not None:
            await self.client.close()


qdrant_client_manager = QdrantClientManager(app_config.qdrant)
