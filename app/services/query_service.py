"""查询服务：编排 LangGraph 图，输出 SSE 事件流（进度事件 + 最终结果）。"""

import json
from collections.abc import AsyncGenerator

from app.agent.context import TournamentAgentContext
from app.agent.graph import graph
from app.agent.state import TournamentAgentState


class QueryService:
    def __init__(self, meta_mysql_repository, embedding_client, dw_mysql_repository,
                 column_qdrant_repository, metric_qdrant_repository, value_es_repository):
        self.meta_mysql_repository = meta_mysql_repository
        self.embedding_client = embedding_client
        self.dw_mysql_repository = dw_mysql_repository
        self.column_qdrant_repository = column_qdrant_repository
        self.metric_qdrant_repository = metric_qdrant_repository
        self.value_es_repository = value_es_repository

    async def query(self, query: str) -> AsyncGenerator[str]:
        state = TournamentAgentState(query=query)
        context = TournamentAgentContext(
            column_qdrant_repository=self.column_qdrant_repository,
            embedding_client=self.embedding_client,
            metric_qdrant_repository=self.metric_qdrant_repository,
            value_es_repository=self.value_es_repository,
            meta_mysql_repository=self.meta_mysql_repository,
            dw_mysql_repository=self.dw_mysql_repository,
        )
        final_state: dict = {}
        async for mode, chunk in graph.astream(input=state, context=context, stream_mode=["custom", "updates"]):
            if mode == "custom":
                # 节点内部 writer 发出的进度事件
                yield f"data: {json.dumps(chunk, ensure_ascii=False, default=str)}\n\n"
            elif mode == "updates":
                # {node_name: state_update}，累积最终状态
                for update in chunk.values():
                    final_state.update(update)
        yield f"data: {json.dumps({'type': 'done', 'result': final_state.get('result'), 'sql': final_state.get('sql'), 'error': final_state.get('error')}, ensure_ascii=False, default=str)}\n\n"
