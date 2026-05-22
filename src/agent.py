from langgraph.graph import StateGraph, START, END

from src.state import AgentState
from src.nodes import split_specification, extract_next_chunk, should_continue, reduce_results


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
workflow.add_edge("reduce_results", END)

graph = workflow.compile()
