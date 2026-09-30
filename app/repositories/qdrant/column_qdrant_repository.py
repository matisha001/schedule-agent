"""ColumnQdrantRepository：字段信息向量召回 + 离线索引写入。

collection 约定为 `column_info`，向量维度取自配置 embedding_size。
- search：在线召回（payload 直接还原 ColumnInfo）
- ensure_collection / upsert：离线构建脚本经 service 编排后调用
"""

from app.clients.qdrant_client_manager import qdrant_client_manager
from app.entities.column_info import ColumnInfo

COLUMN_COLLECTION = "column_info"


class ColumnQdrantRepository:
    async def ensure_collection(self, size: int) -> None:
        """确保字段向量集合存在（embedding_size=size, Distance.COSINE）。"""
        client = qdrant_client_manager.client
        if client is None:
            raise RuntimeError("Qdrant client 未初始化，请检查 lifespan")
        if not await client.collection_exists(COLUMN_COLLECTION):
            await client.create_collection(
                collection_name=COLUMN_COLLECTION,
                vectors_config={"size": size, "distance": "Cosine"},
            )

    async def upsert(self, entries: list[tuple[str, list[float], ColumnInfo]]) -> None:
        """批量写入向量点：entries = [(point_id, vector, ColumnInfo)]，payload 存完整字段信息。"""
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
                    "id": c.id, "name": c.name, "type": c.type, "role": c.role,
                    "examples": c.examples, "description": c.description,
                    "alias": c.alias, "table_id": c.table_id,
                },
            }
            for point_id, vector, c in entries
        ]
        await client.upsert(collection_name=COLUMN_COLLECTION, points=points)

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
