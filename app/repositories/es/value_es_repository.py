"""ValueESRepository：取值字典检索（球队名/赛事名等实体名解析）。"""

from app.clients.es_client_manager import es_client_manager
from app.entities.value_info import ValueInfo

VALUE_INDEX = "value_info"


class ValueESRepository:
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
