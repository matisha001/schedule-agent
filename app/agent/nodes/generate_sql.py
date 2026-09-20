"""节点：生成 SQL（基于召回的元数据）。"""

import json

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import TournamentAgentContext
from app.agent.llm import llm
from app.agent.state import TournamentAgentState
from app.prompt.prompt_loader import load_prompt


def _serialize(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


async def generate_sql(state: TournamentAgentState, runtime: Runtime[TournamentAgentContext]) -> dict:
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "生成 SQL", "status": "running"})

    query = state["query"]
    column_infos = state.get("retrieved_column_infos") or []
    metric_infos = state.get("metric_infos") or []
    value_infos = state.get("retrieved_value_infos") or []
    table_infos = state.get("table_infos") or []

    chain = PromptTemplate(
        template=load_prompt("generate_sql"),
        input_variables=["query", "column_infos", "metric_infos", "value_infos", "table_infos"],
    ) | llm | JsonOutputParser()

    result = await chain.ainvoke({
        "query": query,
        "column_infos": _serialize(column_infos),
        "metric_infos": _serialize(metric_infos),
        "value_infos": _serialize(value_infos),
        "table_infos": _serialize(table_infos),
    })

    sql = str(result.get("sql", "")).strip()
    writer({"type": "progress", "step": "生成 SQL", "status": "success", "sql": sql})
    return {"sql": sql, "error": ""}
