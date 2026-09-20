"""ColumnQdrantRepository：字段信息向量召回。

collection 约定为 `column_info`，向量维度取自配置 embedding_size。
骨架实现：search() 直接调用 Qdrant 检索；建库由离线脚本完成。
"""

from app.clients.qdrant_client_manager import qdrant_client_manager
from app.entities.column_info import ColumnInfo

COLUMN_COLLECTION = "column_info"


class ColumnQdrantRepository:
    async def search(self, embedding: list[float], top_k: int = 8) -> list[ColumnInfo]:
        client = qdrant_client_manager.client
        if client is None:
            raise RuntimeError("Qdrant client 未初始化，请检查 lifespan")
        points = await client.query_points(
            collection_name=COLUMN_COLLECTION,
            query=embedding,
            limit=top_k,
            with_payload=True,
        )
        infos: list[ColumnInfo] = []
        for point in points.points:
            payload = point.payload or {}
            try:
                infos.append(ColumnInfo(**payload))
            except TypeError:
                continue  # 跳过字段缺失的脏数据
        return infos


column_qdrant_repository = ColumnQdrantRepository()
