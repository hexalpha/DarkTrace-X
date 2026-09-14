"""Optional LangGraph orchestration seam for approved, read-only SOC workflows."""

from typing import TypedDict


class InvestigationState(TypedDict):
    question: str
    evidence_refs: list[str]
    summary: str


def build_defensive_summary_graph():
    """Build a tiny graph; wire policy, source retrieval, and audit nodes in deployment code."""
    from langgraph.graph import END, START, StateGraph

    def validate(state: InvestigationState) -> InvestigationState:
        return state

    def compose(state: InvestigationState) -> InvestigationState:
        return {**state, "summary": "Awaiting configured AI provider completion."}

    graph = StateGraph(InvestigationState)
    graph.add_node("validate", validate)
    graph.add_node("compose", compose)
    graph.add_edge(START, "validate")
    graph.add_edge("validate", "compose")
    graph.add_edge("compose", END)
    return graph.compile()

