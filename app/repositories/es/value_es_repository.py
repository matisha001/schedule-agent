"""ValueESRepository：取值字典检索（球队名/赛事名等实体名解析）+ 索引构建。

- 索引名取自配置 es.index_name（构建脚本与在线检索共用同一索引）
- value 字段使用 IK 分词，aliases/field_name 用于辅助匹配
"""

from app.clients.es_client_manager import es_client_manager
from app.entities.value_info import ValueInfo

# 索引名与构建脚本保持一致（配置 es.index_name，如 tournament_agent）
VALUE_INDEX = es_client_manager.config.index_name

# id/field_name 用 keyword 精确匹配；value/aliases 用 text + IK 分词做全文检索
INDEX_MAPPINGS = {
    "dynamic": False,
    "properties": {
        "id": {"type": "keyword"},
        "field_name": {"type": "keyword"},
        "value": {"type": "text", "analyzer": "ik_max_word", "search_analyzer": "ik_max_word"},
        "aliases": {"type": "text", "analyzer": "ik_max_word", "search_analyzer": "ik_max_word"},
        "description": {"type": "text", "analyzer": "ik_max_word", "search_analyzer": "ik_max_word"},
    },
}


class ValueESRepository:
    async def ensure_index(self) -> None:
        """确保取值索引存在（首次写入前由构建脚本调用）。"""
        client = es_client_manager.client
        if client is None:
            raise RuntimeError("ES client 未初始化，请检查 lifespan")
        if not await client.indices.exists(index=VALUE_INDEX):
            await client.indices.create(index=VALUE_INDEX, mappings=INDEX_MAPPINGS)

    async def save_batch(self, infos: list[ValueInfo]) -> int:
        """批量写入取值记录（幂等：同 id 覆盖）。"""
        client = es_client_manager.client
        if client is None:
            raise RuntimeError("ES client 未初始化，请检查 lifespan")
        if not infos:
            return 0
        body: list[dict] = []
        for info in infos:
            body.append({"index": {"_index": VALUE_INDEX, "_id": info.id}})
            body.append({
                "id": info.id,
                "field_name": info.field_name,
                "value": info.value,
                "aliases": info.aliases,
                "description": info.description,
            })
        resp = await client.bulk(operations=body, refresh=True)
        return int(resp.get("items", []).__len__()) if resp.get("errors") is False else 0

    async def search(self, query: str, top_k: int = 8) -> list[ValueInfo]:
        client = es_client_manager.client
        if client is None:
            raise RuntimeError("ES client 未初始化，请检查 lifespan")
        body = {
            "query": {"multi_match": {"query": query, "fields": ["value^2", "aliases", "field_name"]}},
            "size": top_k,
        }
        resp = await client.search(index=VALUE_INDEX, body=body)
        infos: list[ValueInfo] = []
        for hit in resp["hits"]["hits"]:
            src = hit["_source"]
            infos.append(ValueInfo(**src))
        return infos


value_es_repository = ValueESRepository()
