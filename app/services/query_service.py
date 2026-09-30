"""查询服务：编排 LangGraph 图，输出 SSE 事件流（进度事件 + 最终结果）。"""

import json
from collections.abc import AsyncGenerator

from app.agent.context import TournamentAgentContext
from app.agent.graph import graph
from app.agent.state import TournamentAgentState
from app.core.permissions import (
    allowed_tables,
    deny_tables,
    forbid_columns,
    row_scope,
    sensitive_columns,
)
from app.entities.app_user_info import AppUserInfo


class QueryService:
    def __init__(self, meta_mysql_repository, embedding_client, dw_mysql_repository,
                 column_qdrant_repository, metric_qdrant_repository, value_es_repository):
        self.meta_mysql_repository = meta_mysql_repository
        self.embedding_client = embedding_client
        self.dw_mysql_repository = dw_mysql_repository
        self.column_qdrant_repository = column_qdrant_repository
        self.metric_qdrant_repository = metric_qdrant_repository
        self.value_es_repository = value_es_repository

    async def query(
        self, query: str, user: AppUserInfo | None = None
    ) -> AsyncGenerator[str]:
        """执行一次问数，返回 SSE 事件流。

        权限上下文（docs/permission-design.md 第 5 节）：
        - 未登录 → guest 角色（仅公开数据）
        - 登录 → 按 user.role 取权限矩阵，行级注入由 validate_sql 节点确定性校验
        """
        role = user.role if user else "guest"
        user_id = user.id if user else None

        state = TournamentAgentState(query=query)
        context = TournamentAgentContext(
            column_qdrant_repository=self.column_qdrant_repository,
            embedding_client=self.embedding_client,
            metric_qdrant_repository=self.metric_qdrant_repository,
            value_es_repository=self.value_es_repository,
            meta_mysql_repository=self.meta_mysql_repository,
            dw_mysql_repository=self.dw_mysql_repository,
            role=role,
            user_id=user_id,
            allowed_tables=allowed_tables(role),
            deny_tables=deny_tables(role),
            sensitive_columns=sensitive_columns(),
            forbid_columns=forbid_columns(),
            row_scope=row_scope(role),
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
