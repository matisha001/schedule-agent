"""节点：提取查询关键词（jieba + LLM 结构化提取）。"""

import json

import jieba
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import TournamentAgentContext
from app.agent.llm import llm
from app.agent.state import TournamentAgentState
from app.prompt.prompt_loader import load_prompt

_STOP_WORDS = {"的", "了", "呢", "吗", "在", "是", "有", "和", "与", "及", "或", "请", "帮我", "一下", "哪些", "什么"}


async def extract_keywords(state: TournamentAgentState, runtime: Runtime[TournamentAgentContext]) -> dict:
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "提取关键词", "status": "running"})

    query = state["query"]

    # jieba 基础分词（离线兜底）
    jieba_keywords = [w.strip() for w in jieba.cut_for_search(query) if w.strip() and w.strip() not in _STOP_WORDS]

    # LLM 结构化提取
    chain = PromptTemplate(
        template=load_prompt("extract_keywords"),
        input_variables=["query"],
    ) | llm | JsonOutputParser()

    llm_keywords: list[str] = []
    try:
        raw = await chain.ainvoke({"query": query})
        if isinstance(raw, list):
            llm_keywords = [str(k).strip() for k in raw if str(k).strip()]
    except json.JSONDecodeError:
        writer({"type": "progress", "step": "提取关键词", "status": "warning", "message": "LLM 输出非 JSON，使用 jieba 结果"})

    keywords = list(dict.fromkeys(jieba_keywords + llm_keywords))
    writer({"type": "progress", "step": "提取关键词", "status": "success", "keywords": keywords})
    return {"keywords": keywords}
