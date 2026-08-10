from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
from app.agents.state import AgentState
from app.agents.nodes import planner_node, researcher_node, synthesizer_node
from app.db.models import WorkflowStatus

def should_continue(state: AgentState) -> Literal["researcher", "synthesizer"]:
    """
    Conditional routing logic detailing how control passes from Researcher back to Researcher
    for additional steps or transitions to Synthesizer when research is complete.
    """
    current_idx = state.get("current_step_index", 0)
    plan = state.get("plan", [])
    
    if current_idx < len(plan):
        return "researcher"
    else:
        return "synthesizer"

def build_agent_graph():
    """
    Constructs and compiles the LangGraph state machine for multi-agent orchestration.
    Graph Flow: ENTRY -> Planner -> Researcher -> (Loop or Synthesizer) -> END
    """
    builder = StateGraph(AgentState)

    # Add agent nodes
    builder.add_node("planner", planner_node)
    builder.add_node("researcher", researcher_node)
    builder.add_node("synthesizer", synthesizer_node)

    # Entry point & static edges
    builder.set_entry_point("planner")
    builder.add_edge("planner", "researcher")

    # Conditional routing edge from Researcher
    builder.add_conditional_edges(
        "researcher",
        should_continue,
        {
            "researcher": "researcher",
            "synthesizer": "synthesizer"
        }
    )

    # Terminal edge
    builder.add_edge("synthesizer", END)

    return builder.compile()

# Singleton compiled graph instance
agent_workflow_graph = build_agent_graph()

def run_agent_workflow(task_id: str, prompt: str) -> AgentState:
    """
    Executes the multi-agent orchestration workflow for a specific task_id and prompt.
    """
    initial_state: AgentState = {
        "task_id": task_id,
        "prompt": prompt,
        "plan": [],
        "current_step_index": 0,
        "research_data": [],
        "messages": [],
        "final_result": None,
        "status": WorkflowStatus.PENDING.value,
        "error": None
    }

    # Execute graph state machine
    final_state = agent_workflow_graph.invoke(initial_state)
    return final_state
