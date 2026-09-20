"""Elasticsearch 客户端管理器（存赛事取值字典，如球队名/赛事名/比分等）。"""

import sys
from pathlib import Path

from elasticsearch import AsyncElasticsearch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.conf.app_config import ESConfig, app_config


class ESClientManager:
    def __init__(self, config: ESConfig):
        self.client: AsyncElasticsearch | None = None
        self.config = config

    def init(self):
        self.client = AsyncElasticsearch(hosts=[f"http://{self.config.host}:{self.config.port}"])

    async def close(self):
        if self.client is not None:
            await self.client.close()


es_client_manager = ESClientManager(app_config.es)
