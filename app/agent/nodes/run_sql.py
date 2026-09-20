"""节点：执行 SQL 并返回结果。"""

from langgraph.runtime import Runtime

from app.agent.context import TournamentAgentContext
from app.agent.state import TournamentAgentState


async def run_sql(state: TournamentAgentState, runtime: Runtime[TournamentAgentContext]) -> dict:
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "执行查询", "status": "running"})

    sql = state.get("sql", "")
    dw_repo = runtime.context["dw_mysql_repository"]

    try:
        columns, rows = await dw_repo.run_select(sql)
        writer({"type": "progress", "step": "执行查询", "status": "success", "rows": len(rows)})
        return {"result": {"columns": columns, "rows": rows}, "error": ""}
    except Exception as exc:  # noqa: BLE001 - SQL 执行失败交由 correct_sql 修正
        writer({"type": "progress", "step": "执行查询", "status": "error", "message": str(exc)})
        return {"error": f"执行失败：{exc}"}
