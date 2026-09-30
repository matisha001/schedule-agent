"""Elasticsearch 客户端管理器（存赛事取值字典，如球队名/赛事名/比分等）。

注意：部分机器 /etc/hosts 缺少 localhost 映射（如 SwitchHosts 接管），
驱动层会报 nodename nor servname；此处把 localhost 解析为 127.0.0.1。
"""

import sys
from pathlib import Path

from elasticsearch import AsyncElasticsearch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.conf.app_config import ESConfig, app_config


def _resolve_host(host: str) -> str:
    """驱动层兼容：localhost → 127.0.0.1。"""
    return "127.0.0.1" if host == "localhost" else host


class ESClientManager:
    def __init__(self, config: ESConfig):
        self.client: AsyncElasticsearch | None = None
        self.config = config

    def init(self):
        self.client = AsyncElasticsearch(hosts=[f"http://{_resolve_host(self.config.host)}:{self.config.port}"])

    async def close(self):
        if self.client is not None:
            await self.client.close()


es_client_manager = ESClientManager(app_config.es)
