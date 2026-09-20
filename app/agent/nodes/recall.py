"""节点：多路召回——字段/指标向量召回 + 取值字典检索，并聚合表结构摘要。"""

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import TournamentAgentContext
from app.agent.llm import llm
from app.agent.state import TournamentAgentState
from app.prompt.prompt_loader import load_prompt


async def recall(state: TournamentAgentState, runtime: Runtime[TournamentAgentContext]) -> dict:
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "召回知识", "status": "running"})

    query = state["query"]
    keywords = state.get("keywords") or [query]
    column_repo = runtime.context["column_qdrant_repository"]
    metric_repo = runtime.context["metric_qdrant_repository"]
    value_repo = runtime.context["value_es_repository"]
    embedding_client = runtime.context["embedding_client"]

    # LLM 扩展召回关键词（一次调用）
    try:
        chain = PromptTemplate(
            template=load_prompt("extend_keywords_for_column_recall"),
            input_variables=["query"],
        ) | llm | JsonOutputParser()
        extended = await chain.ainvoke({"query": query})
        keyword_list = list(dict.fromkeys(keywords + [str(k) for k in extended]))
    except Exception:  # noqa: BLE001 - LLM 扩展失败时退化为原始关键词
        keyword_list = keywords

    # 批量向量化（一次 API 调用）
    try:
        embeddings = await embedding_client.aembed_documents(keyword_list)
    except Exception as exc:  # noqa: BLE001 - 外部服务未就绪时给出可读错误
        writer({"type": "progress", "step": "召回知识", "status": "error", "message": str(exc)})
        return {"retrieved_column_infos": [], "retrieved_metric_infos": [], "retrieved_value_infos": [], "table_infos": []}

    # Qdrant 本地检索（按 id 去重合并）
    column_map, metric_map = {}, {}
    for embedding in embeddings:
        for info in await column_repo.search(embedding):
            column_map[info.id] = info
        for info in await metric_repo.search(embedding):
            metric_map[info.id] = info

    # ES 取值字典检索（取用户问题本身）
    value_infos = []
    try:
        value_infos = await value_repo.search(query)
    except Exception as exc:  # noqa: BLE001 - ES 不可用时降级
        writer({"type": "progress", "step": "召回知识", "status": "warning", "message": f"ES 检索失败：{exc}"})

    columns = list(column_map.values())
    metrics = list(metric_map.values())

    # 聚合表结构摘要：按 table_id 分组
    table_map: dict[str, dict] = {}
    for col in columns:
        tbl = table_map.setdefault(col.table_id, {"table_id": col.table_id, "columns": []})
        tbl["columns"].append({"name": col.name, "type": col.type, "role": col.role, "description": col.description})

    writer({"type": "progress", "step": "召回知识", "status": "success",
            "hits": {"columns": len(columns), "metrics": len(metrics), "values": len(value_infos)}})

    return {
        "retrieved_column_infos": columns,
        "retrieved_metric_infos": metrics,
        "retrieved_value_infos": value_infos,
        "table_infos": list(table_map.values()),
        "metric_infos": [
            {"name": m.name, "expression": m.expression, "description": m.description, "table_id": m.table_id}
            for m in metrics
        ],
    }
