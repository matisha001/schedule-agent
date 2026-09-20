"""LangGraph 图定义：赛事问数工作流。

节点链：提取关键词 → 多路召回 → 生成 SQL → 校验 →（修正/执行）→ 结束
"""

import sys
from pathlib import Path

from langgraph.constants import END, START
from langgraph.graph import StateGraph

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.agent.context import TournamentAgentContext
from app.agent.nodes.correct_sql import correct_sql
from app.agent.nodes.extract_keywords import extract_keywords
from app.agent.nodes.generate_sql import generate_sql
from app.agent.nodes.recall import recall
from app.agent.nodes.run_sql import run_sql
from app.agent.nodes.validate_sql import validate_sql
from app.agent.state import TournamentAgentState

graph_builder = StateGraph(state_schema=TournamentAgentState, context_schema=TournamentAgentContext)

# 节点
graph_builder.add_node("extract_keywords", extract_keywords)
graph_builder.add_node("recall", recall)
graph_builder.add_node("generate_sql", generate_sql)
graph_builder.add_node("validate_sql", validate_sql)
graph_builder.add_node("run_sql", run_sql)
graph_builder.add_node("correct_sql", correct_sql)

# 边
graph_builder.add_edge(START, "extract_keywords")
graph_builder.add_edge("extract_keywords", "recall")
graph_builder.add_edge("recall", "generate_sql")
graph_builder.add_edge("generate_sql", "validate_sql")
graph_builder.add_edge("correct_sql", "generate_sql")

# 条件边：校验通过则执行，否则修正后重新生成
graph_builder.add_conditional_edges(
    source="validate_sql",
    path=lambda state: "run_sql" if not state.get("error") else "correct_sql",
    path_map={"run_sql": "run_sql", "correct_sql": "correct_sql"},
)
graph_builder.add_edge("run_sql", END)

graph = graph_builder.compile()
