from typing import TypedDict, List, Dict, Any, Optional
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    """
    Shared state object passed between agents during LangGraph execution.
    Contains task details, multi-step plan, gathered tool results, message history,
    and final synthesized response.
    """
    task_id: str
    prompt: str
    plan: List[str]
    current_step_index: int
    research_data: List[Dict[str, Any]]
    messages: List[BaseMessage]
    final_result: Optional[str]
    status: str
    error: Optional[str]
