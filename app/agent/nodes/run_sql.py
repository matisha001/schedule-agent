"""
SQL 执行节点

负责执行最终 SQL，并记录查询结果。
它是当前 SQL 闭环的结束节点，执行完成后流程进入 END。
"""

from langgraph.runtime import Runtime

from app.agent.context import TournamentAgentContext
from app.agent.state import TournamentAgentState
from app.core.log import logger


async def run_sql(
    state: TournamentAgentState, runtime: Runtime[TournamentAgentContext]
):
    """执行 SQL 并产出最终问数结果"""

    writer = runtime.stream_writer
    step = "执行SQL"
    writer({"type": "progress", "step": step, "status": "running"})

    try:
        # 这里拿到的可能是 generate_sql 直接通过校验的 SQL，也可能是 correct_sql 覆盖后的 SQL
        sql = state["sql"]
        dw_mysql_repository = runtime.context["dw_mysql_repository"]

        # 真实数据库访问统一封装在仓储层，节点只负责从状态取 SQL 并触发执行
        columns, rows = await dw_mysql_repository.run_select(sql)
        result = {"columns": columns, "rows": rows}
        logger.info(f"SQL执行结果：{result}")
        writer({"type": "progress", "step": step, "status": "success"})
        writer({"type": "result", "data": result})

        # 结果和错误写回 state，供查询服务在 SSE done 事件中统一返回给前端
        return {"result": result, "error": None}
    except Exception as e:
        logger.error(f"{step} failed: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        # 执行失败不中断图执行，把错误写回 state 交给 SSE done 事件展示
        return {"error": f"执行失败：{e}"}
