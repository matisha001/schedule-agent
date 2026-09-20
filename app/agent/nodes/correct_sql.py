"""节点：根据校验/执行错误修正 SQL。"""

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import TournamentAgentContext
from app.agent.llm import llm
from app.agent.state import TournamentAgentState
from app.prompt.prompt_loader import load_prompt


async def correct_sql(state: TournamentAgentState, runtime: Runtime[TournamentAgentContext]) -> dict:
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "修正 SQL", "status": "running"})

    chain = PromptTemplate(
        template=load_prompt("correct_sql"),
        input_variables=["sql", "error", "query", "column_infos"],
    ) | llm | JsonOutputParser()

    result = await chain.ainvoke({
        "sql": state.get("sql", ""),
        "error": state.get("error", ""),
        "query": state["query"],
        "column_infos": _serialize(state.get("retrieved_column_infos") or []),
    })

    sql = str(result.get("sql", "")).strip()
    writer({"type": "progress", "step": "修正 SQL", "status": "success", "sql": sql})
    return {"sql": sql, "error": ""}


def _serialize(obj) -> str:
    import json
    return json.dumps(obj, ensure_ascii=False, default=str)
