"""离线构建知识库脚本：把 meta 库元数据写入 Qdrant（字段/指标向量）与 ES（取值字典）。

用法：uv run python -m app.scripts.build_meta_knowledge
依赖：MySQL/Qdrant/ES 已启动，meta 库已灌入元数据。
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from loguru import logger

from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.mysql_client_manager import meta_mysql_client_manager
from app.clients.qdrant_client_manager import qdrant_client_manager
from app.repositories.mysql.meta.meta_mysql_repository import meta_mysql_repository
from app.repositories.qdrant.column_qdrant_repository import COLUMN_COLLECTION
from app.repositories.qdrant.metric_qdrant_repository import METRIC_COLLECTION


async def _ensure_qdrant_collection(name: str, size: int) -> None:
    client = qdrant_client_manager.client
    if client is None:
        raise RuntimeError("Qdrant client 未初始化")
    if not await client.collection_exists(name):
        await client.create_collection(
            collection_name=name,
            vectors_config={"size": size, "distance": "Cosine"},
        )
        logger.info("创建 Qdrant collection: {}", name)


async def _index_columns(embedding_size: int) -> None:
    columns = await meta_mysql_repository.list_all_columns()
    if not columns:
        logger.warning("meta 库 column_info 为空，跳过字段向量化")
        return
    client = qdrant_client_manager.client
    texts = [f"{c.name} {c.description} {' '.join(c.alias)}" for c in columns]
    embeddings = await embedding_client_manager.client.aembed_documents(texts)
    points = [
        {
            "id": c.id,
            "vector": emb,
            "payload": {
                "id": c.id, "name": c.name, "type": c.type, "role": c.role,
                "examples": c.examples, "description": c.description,
                "alias": c.alias, "table_id": c.table_id,
            },
        }
        for c, emb in zip(columns, embeddings, strict=False)
    ]
    await client.upsert(collection_name=COLUMN_COLLECTION, points=points)
    logger.info("字段元数据入库 Qdrant: {} 条", len(points))


async def _index_metrics(embedding_size: int) -> None:
    # TODO(待领域信息补充): 指标数据源与向量化文案
    logger.info("metric_info 构建逻辑待领域信息补充后实现")


async def _index_values() -> None:
    # TODO(待领域信息补充): 从 meta 库 value_info 灌入 ES
    logger.info("value_info 构建逻辑待领域信息补充后实现")


async def main() -> None:
    qdrant_client_manager.init()
    embedding_client_manager.init()
    es_client_manager.init()
    meta_mysql_client_manager.init()

    size = qdrant_client_manager.config.embedding_size
    await _ensure_qdrant_collection(COLUMN_COLLECTION, size)
    await _ensure_qdrant_collection(METRIC_COLLECTION, size)
    # ES 索引可在首次写入时自动创建，骨架阶段跳过

    await _index_columns(size)
    await _index_metrics(size)
    await _index_values()

    await qdrant_client_manager.close()
    await es_client_manager.close()
    await meta_mysql_client_manager.close()
    logger.info("知识库构建完成")


if __name__ == "__main__":
    asyncio.run(main())
