"""LangGraph state definition."""
from typing import TypedDict, List, Dict, Any, Annotated
from langgraph.graph import add_messages


class MemoryState(TypedDict):
    """
    State cho LangGraph memory agent.
    
    Attributes:
        messages: Conversation messages (managed by add_messages)
        user_id: User identifier
        user_profile: Long-term profile facts
        episodes: Relevant episodic memories
        semantic_hits: Semantic search results
        memory_budget: Token budget cho memory injection
        final_response: Response từ LLM
    """
    messages: Annotated[List[Dict[str, str]], add_messages]
    user_id: str
    user_profile: Dict[str, Any]
    episodes: List[Dict[str, Any]]
    semantic_hits: List[Dict[str, Any]]
    memory_budget: int
    final_response: str
