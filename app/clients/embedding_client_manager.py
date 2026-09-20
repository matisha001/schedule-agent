"""Embedding 客户端管理器（中文向量模型，用于 Qdrant 召回）。"""

import sys
from pathlib import Path

from langchain_openai import OpenAIEmbeddings

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.conf.app_config import EmbeddingConfig, app_config


class EmbeddingClientManager:
    def __init__(self, config: EmbeddingConfig):
        self.client: OpenAIEmbeddings | None = None
        self.config = config

    def init(self):
        self.client = OpenAIEmbeddings(
            model=self.config.model,
            base_url=self.config.base_url,
            api_key=self.config.api_key,
            check_embedding_ctx_length=False,  # 第三方 API 不接受 token ID
        )


embedding_client_manager = EmbeddingClientManager(app_config.embedding)
