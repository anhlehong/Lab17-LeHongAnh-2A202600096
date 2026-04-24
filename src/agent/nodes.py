"""LangGraph nodes for memory agent."""
from typing import Dict, Any
from .state import MemoryState
from ..memory import ShortTermMemory, ProfileMemory, EpisodicMemory, SemanticMemory
from ..llm import LLMClient
from ..utils.prompt_builder import build_prompt_with_memory


def retrieve_memory_node(
    state: MemoryState,
    short_term: ShortTermMemory,
    profile: ProfileMemory,
    episodic: EpisodicMemory,
    semantic: SemanticMemory
) -> Dict[str, Any]:
    """
    Node: Retrieve memory từ 4 backends.
    
    Args:
        state: Current state
        short_term: Short-term memory instance
        profile: Profile memory instance
        episodic: Episodic memory instance
        semantic: Semantic memory instance
        
    Returns:
        Updated state với memory data
    """
    # Get current user message
    messages = state.get("messages", [])
    if not messages:
        return state
    
    # Handle both dict and LangChain message objects
    last_msg = messages[-1]
    if hasattr(last_msg, 'content'):
        last_message = last_msg.content
    elif isinstance(last_msg, dict):
        last_message = last_msg.get("content", "")
    else:
        last_message = str(last_msg)
    
    # 1. Short-term: Already in messages
    # (LangGraph manages messages automatically)
    
    # 2. Profile: Get user facts
    user_profile = profile.get_profile()
    
    # 3. Episodic: Search relevant episodes
    episodes = episodic.search_episodes(last_message, limit=3)
    
    # 4. Semantic: Search documents
    semantic_hits = semantic.search(last_message, top_k=3)
    
    return {
        **state,
        "user_profile": user_profile,
        "episodes": episodes,
        "semantic_hits": semantic_hits
    }


def process_with_llm_node(
    state: MemoryState,
    llm_client: LLMClient,
    short_term: ShortTermMemory
) -> Dict[str, Any]:
    """
    Node: Process với LLM, inject memory vào prompt.
    
    Args:
        state: Current state
        llm_client: LLM client instance
        short_term: Short-term memory instance
        
    Returns:
        Updated state với LLM response
    """
    messages = state.get("messages", [])
    if not messages:
        return state
    
    # Get current user message - handle both dict and LangChain objects
    last_msg = messages[-1]
    if hasattr(last_msg, 'content'):
        user_message = last_msg.content
    elif isinstance(last_msg, dict):
        user_message = last_msg.get("content", "")
    else:
        user_message = str(last_msg)
    
    # Get memory data
    user_profile = state.get("user_profile", {})
    episodes = state.get("episodes", [])
    semantic_hits = state.get("semantic_hits", [])
    memory_budget = state.get("memory_budget", 2000)
    
    # Get recent conversation from short-term
    recent_conversation = short_term.get_recent_text(num_messages=6)
    
    # Build prompt with memory injection
    prompt_messages = build_prompt_with_memory(
        user_message=user_message,
        user_profile=user_profile,
        episodes=episodes,
        semantic_hits=semantic_hits,
        recent_conversation=recent_conversation,
        memory_budget=memory_budget
    )
    
    # Call LLM
    response = llm_client.chat(prompt_messages)
    
    return {
        **state,
        "final_response": response
    }


def save_memory_node(
    state: MemoryState,
    llm_client: LLMClient,
    short_term: ShortTermMemory,
    profile: ProfileMemory,
    episodic: EpisodicMemory
) -> Dict[str, Any]:
    """
    Node: Save/update memory sau khi xử lý.
    
    Args:
        state: Current state
        llm_client: LLM client instance
        short_term: Short-term memory instance
        profile: Profile memory instance
        episodic: Episodic memory instance
        
    Returns:
        Updated state
    """
    messages = state.get("messages", [])
    response = state.get("final_response", "")
    
    if not messages or not response:
        return state
    
    # Add to short-term memory - handle both dict and LangChain objects
    last_msg = messages[-1]
    if hasattr(last_msg, 'content'):
        user_message = last_msg.content
    elif isinstance(last_msg, dict):
        user_message = last_msg.get("content", "")
    else:
        user_message = str(last_msg)
    short_term.add_message("user", user_message)
    short_term.add_message("assistant", response)
    
    # Get recent conversation for analysis
    recent_conv = short_term.get_recent_text(num_messages=4)
    
    # Extract and update profile facts
    current_profile = state.get("user_profile", {})
    new_facts = llm_client.extract_facts(recent_conv, current_profile)
    
    if new_facts:
        profile.update_facts(new_facts)
        print(f"[OK] Updated profile: {new_facts}")
    
    # Check if should save episode
    should_save, episode_data = llm_client.should_save_episode(recent_conv)
    
    if should_save and episode_data:
        episodic.add_episode(episode_data)
        print(f"[OK] Saved episode: {episode_data['title']}")
    
    return state
