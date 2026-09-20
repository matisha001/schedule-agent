"""MetricQdrantRepository：指标信息向量召回。"""

from app.clients.qdrant_client_manager import qdrant_client_manager
from app.entities.metric_info import MetricInfo

METRIC_COLLECTION = "metric_info"


class MetricQdrantRepository:
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
                continue
        return infos


metric_qdrant_repository = MetricQdrantRepository()
