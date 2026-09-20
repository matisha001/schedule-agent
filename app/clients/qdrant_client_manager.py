"""Qdrant 向量库客户端管理器（存字段/赛事术语等知识向量）。"""

import sys
from pathlib import Path

from qdrant_client import AsyncQdrantClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.conf.app_config import QdrantConfig, app_config


class QdrantClientManager:
    def __init__(self, config: QdrantConfig):
        self.client: AsyncQdrantClient | None = None
        self.config = config

    def init(self):
        self.client = AsyncQdrantClient(url=f"http://{self.config.host}:{self.config.port}")

    async def close(self):
        if self.client is not None:
            await self.client.close()


qdrant_client_manager = QdrantClientManager(app_config.qdrant)
