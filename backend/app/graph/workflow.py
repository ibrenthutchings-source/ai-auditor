from langgraph.graph import END, START, StateGraph

from app.agents.bias_agent import bias_evaluator_node
from app.agents.hitl_agent import hitl_evaluator_node
from app.agents.lead_auditor import synthesis_node
from app.agents.security_agent import security_evaluator_node
from app.graph.state import GraphState
from app.recommender.engine import recommender_node


def intake_node(state: GraphState) -> dict:
    if not state.get("target_system_logs"):
        return {"errors": ["No target_system_logs provided"], "current_status": "FAILED"}
    return {"current_status": "IN_PROGRESS"}


def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("intake_node", intake_node)
    graph.add_node("bias_evaluator_node", bias_evaluator_node)
    graph.add_node("security_evaluator_node", security_evaluator_node)
    graph.add_node("hitl_evaluator_node", hitl_evaluator_node)
    graph.add_node("synthesis_node", synthesis_node)
    graph.add_node("recommender_node", recommender_node)

    graph.add_edge(START, "intake_node")

    # Parallel fan-out: all three evaluators run off intake, LangGraph
    # dedupes the fan-in barrier at synthesis_node automatically.
    graph.add_edge("intake_node", "bias_evaluator_node")
    graph.add_edge("intake_node", "security_evaluator_node")
    graph.add_edge("intake_node", "hitl_evaluator_node")

    graph.add_edge("bias_evaluator_node", "synthesis_node")
    graph.add_edge("security_evaluator_node", "synthesis_node")
    graph.add_edge("hitl_evaluator_node", "synthesis_node")

    graph.add_edge("synthesis_node", "recommender_node")
    graph.add_edge("recommender_node", END)

    return graph.compile()


audit_graph = build_graph()
