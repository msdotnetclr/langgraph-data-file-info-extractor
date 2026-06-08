from langgraph.graph import StateGraph, START, END

from src.state import AgentState
from src.nodes import (
    split_specification,
    extract_next_chunk,
    should_continue,
    reduce_results,
    review_results,
    incorporate_feedback,
    after_review_route,
    store_approved_result,
)


def _build_base_workflow() -> StateGraph:
    workflow = StateGraph(AgentState)

    workflow.add_node("split_specification", split_specification)
    workflow.add_node("extract_next_chunk", extract_next_chunk)
    workflow.add_node("reduce_results", reduce_results)

    workflow.add_edge(START, "split_specification")
    workflow.add_edge("split_specification", "extract_next_chunk")
    workflow.add_conditional_edges("extract_next_chunk", should_continue, {
        "extract_next_chunk": "extract_next_chunk",
        "reduce_results": "reduce_results",
    })

    return workflow


def build_graph():
    workflow = _build_base_workflow()
    workflow.add_edge("reduce_results", END)
    return workflow.compile()


def build_interactive_graph(checkpointer):
    workflow = _build_base_workflow()

    workflow.add_node("review_results", review_results)
    workflow.add_node("incorporate_feedback", incorporate_feedback)
    workflow.add_node("store_approved_result", store_approved_result)

    workflow.add_edge("reduce_results", "review_results")
    workflow.add_conditional_edges("review_results", after_review_route, {
        "store_approved_result": "store_approved_result",
        "incorporate_feedback": "incorporate_feedback",
        "reduce_results": "reduce_results",
    })
    workflow.add_edge("incorporate_feedback", "split_specification")
    workflow.add_edge("store_approved_result", END)

    return workflow.compile(checkpointer=checkpointer)


graph = build_graph()
