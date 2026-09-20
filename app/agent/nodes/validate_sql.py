"""节点：校验 SQL（只读约束 + 语法/语义检查）。"""

import re

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import TournamentAgentContext
from app.agent.llm import llm
from app.agent.state import TournamentAgentState
from app.prompt.prompt_loader import load_prompt

# 基础只读防线：仅允许 SELECT / WITH 开头的单条语句
_READ_ONLY_RE = re.compile(r"^\s*(SELECT|WITH)\b", re.IGNORECASE)
_MULTI_STMT_RE = re.compile(r";\s*\S")


async def validate_sql(state: TournamentAgentState, runtime: Runtime[TournamentAgentContext]) -> dict:
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "校验 SQL", "status": "running"})

    sql = state.get("sql", "")
    error = ""

    # 规则 1：只读 + 单语句
    if not sql or not _READ_ONLY_RE.match(sql):
        error = "仅允许 SELECT/WITH 只读查询"
    elif _MULTI_STMT_RE.search(sql):
        error = "不允许执行多条语句"

    # 规则 2：LLM 语义校验（可放宽失败为 warning）
    if not error:
        try:
            chain = PromptTemplate(
                template=load_prompt("validate_sql"),
                input_variables=["sql", "table_infos"],
            ) | llm | JsonOutputParser()
            verdict = await chain.ainvoke({"sql": sql, "table_infos": _serialize(state.get("table_infos") or [])})
            if verdict.get("valid") is False:
                error = str(verdict.get("error") or "SQL 校验未通过")
        except Exception as exc:  # noqa: BLE001 - LLM 校验不可用时仅保留规则校验
            writer({"type": "progress", "step": "校验 SQL", "status": "warning", "message": f"LLM 校验跳过：{exc}"})

    writer({"type": "progress", "step": "校验 SQL", "status": "success" if not error else "error", "error": error})
    return {"error": error}


def _serialize(obj) -> str:
    import json
    return json.dumps(obj, ensure_ascii=False, default=str)
