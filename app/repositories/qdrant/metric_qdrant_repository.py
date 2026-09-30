"""MetricQdrantRepository：指标信息向量召回 + 离线索引写入。

collection 约定为 `metric_info`，向量维度取自配置 embedding_size。
- search：在线召回（payload 直接还原 MetricInfo）
- ensure_collection / upsert：离线构建脚本经 service 编排后调用
"""

from app.clients.qdrant_client_manager import qdrant_client_manager
from app.entities.metric_info import MetricInfo

METRIC_COLLECTION = "metric_info"


class MetricQdrantRepository:
    async def ensure_collection(self, size: int) -> None:
        """确保指标向量集合存在（embedding_size=size, Distance.COSINE）。"""
        client = qdrant_client_manager.client
        if client is None:
            raise RuntimeError("Qdrant client 未初始化，请检查 lifespan")
        if not await client.collection_exists(METRIC_COLLECTION):
            await client.create_collection(
                collection_name=METRIC_COLLECTION,
                vectors_config={"size": size, "distance": "Cosine"},
            )

    async def upsert(self, entries: list[tuple[str, list[float], MetricInfo]]) -> None:
        """批量写入向量点：entries = [(point_id, vector, MetricInfo)]，payload 存完整指标信息。"""
        client = qdrant_client_manager.client
        if client is None:
            raise RuntimeError("Qdrant client 未初始化，请检查 lifespan")
        if not entries:
            return
        points = [
            {
                "id": point_id,
                "vector": vector,
                "payload": {
                    "id": m.id, "name": m.name, "agg_type": m.agg_type,
                    "expression": m.expression, "description": m.description,
                    "alias": m.alias, "table_id": m.table_id,
                },
            }
            for point_id, vector, m in entries
        ]
        await client.upsert(collection_name=METRIC_COLLECTION, points=points)

    async def search(self, embedding: list[float], top_k: int = 8) -> list[MetricInfo]:
        client = qdrant_client_manager.client
        if client is None:
            raise RuntimeError("Qdrant client 未初始化，请检查 lifespan")
        points = await client.query_points(
            collection_name=METRIC_COLLECTION,
            query=embedding,
            limit=top_k,
            with_payload=True,
        )
        infos: list[MetricInfo] = []
        for point in points.points:
            payload = point.payload or {}
            try:
                infos.append(MetricInfo(**payload))
            except TypeError:
                continue  # 跳过字段缺失的脏数据
        return infos


metric_qdrant_repository = MetricQdrantRepository()
