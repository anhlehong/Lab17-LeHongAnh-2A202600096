"""LangGraph workflow for memory agent."""
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from .state import MemoryState
from .nodes import retrieve_memory_node, process_with_llm_node, save_memory_node
from ..memory import ShortTermMemory, ProfileMemory, EpisodicMemory, SemanticMemory
from ..llm import LLMClient


class MemoryAgent:
    """
    Multi-Memory Agent với LangGraph.
    
    Flow:
        START → retrieve_memory → process_with_llm → save_memory → END
    """
    
    def __init__(self, user_id: str, use_redis: bool = True):
        """
        Args:
            user_id: User identifier
            use_redis: Có dùng Redis không (fallback to dict)
        """
        self.user_id = user_id
        
        # Initialize memory backends
        self.short_term = ShortTermMemory(max_messages=10)
        self.profile = ProfileMemory(user_id, use_redis=use_redis)
        self.episodic = EpisodicMemory(user_id)
        self.semantic = SemanticMemory()
        
        # Initialize LLM client
        self.llm_client = LLMClient()
        
        # Build LangGraph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build LangGraph workflow."""
        workflow = StateGraph(MemoryState)
        
        # Add nodes
        workflow.add_node(
            "retrieve_memory",
            lambda state: retrieve_memory_node(
                state,
                self.short_term,
                self.profile,
                self.episodic,
                self.semantic
            )
        )
        
        workflow.add_node(
            "process_with_llm",
            lambda state: process_with_llm_node(
                state,
                self.llm_client,
                self.short_term
            )
        )
        
        workflow.add_node(
            "save_memory",
            lambda state: save_memory_node(
                state,
                self.llm_client,
                self.short_term,
                self.profile,
                self.episodic
            )
        )
        
        # Add edges
        workflow.set_entry_point("retrieve_memory")
        workflow.add_edge("retrieve_memory", "process_with_llm")
        workflow.add_edge("process_with_llm", "save_memory")
        workflow.add_edge("save_memory", END)
        
        return workflow.compile()
    
    def load_semantic_docs(self, directory: str = "data/docs"):
        """Load documents vào semantic memory."""
        self.semantic.load_from_directory(directory)
    
    def invoke(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke agent với input.
        
        Args:
            input_data: {"messages": [{"role": "user", "content": "..."}]}
            
        Returns:
            State với final_response
        """
        # Prepare initial state
        state = {
            "messages": input_data.get("messages", []),
            "user_id": self.user_id,
            "user_profile": {},
            "episodes": [],
            "semantic_hits": [],
            "memory_budget": 2000,
            "final_response": ""
        }
        
        # Run graph
        result = self.graph.invoke(state)
        
        return result
    
    def chat(self, user_message: str) -> str:
        """
        Simple chat interface.
        
        Args:
            user_message: User's message
            
        Returns:
            Agent's response
        """
        result = self.invoke({
            "messages": [{"role": "user", "content": user_message}]
        })
        
        return result.get("final_response", "")


def create_memory_agent(user_id: str, use_redis: bool = True) -> MemoryAgent:
    """
    Factory function để tạo memory agent.
    
    Args:
        user_id: User identifier
        use_redis: Có dùng Redis không
        
    Returns:
        MemoryAgent instance
    """
    agent = MemoryAgent(user_id, use_redis=use_redis)
    
    # Load semantic documents
    agent.load_semantic_docs()
    
    return agent
