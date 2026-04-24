"""Prompt building with memory injection."""
from typing import Dict, List, Any
from .token_counter import estimate_tokens, trim_to_budget


def build_prompt_with_memory(
    user_message: str,
    user_profile: Dict[str, Any],
    episodes: List[Dict[str, Any]],
    semantic_hits: List[Dict[str, Any]],
    recent_conversation: str,
    memory_budget: int = 2000
) -> List[Dict[str, str]]:
    """
    Build prompt với memory injection từ 4 memory types.
    
    Args:
        user_message: Current user message
        user_profile: Long-term profile facts
        episodes: Relevant episodic memories
        semantic_hits: Semantic search results
        recent_conversation: Short-term conversation
        memory_budget: Token budget cho memory sections
        
    Returns:
        Messages list cho LLM
    """
    # System prompt
    system_prompt = """Bạn là trợ lý AI thông minh với khả năng ghi nhớ.

Bạn có quyền truy cập vào:
1. Thông tin cá nhân của user (profile)
2. Các episodes/tasks trước đây (episodic memory)
3. Documents/FAQs liên quan (semantic memory)
4. Hội thoại gần đây (short-term memory)

Nhiệm vụ:
- Sử dụng memory để cung cấp câu trả lời cá nhân hóa và chính xác
- Nhớ thông tin user đã chia sẻ
- Học từ các episodes trước
- Tham khảo documents khi cần

Hãy trả lời một cách tự nhiên và hữu ích."""
    
    # Build memory sections
    sections = []
    
    # 1. User profile
    if user_profile:
        profile_text = "=== THÔNG TIN USER ===\n"
        for key, value in user_profile.items():
            profile_text += f"- {key}: {value}\n"
        sections.append(("profile", profile_text))
    
    # 2. Episodes
    if episodes:
        ep_text = "\n=== EPISODES TRƯỚC ĐÂY ===\n"
        for i, ep in enumerate(episodes[:3], 1):  # Max 3 episodes
            ep_text += f"\n{i}. {ep.get('title', 'Unknown')}\n"
            if ep.get('outcome'):
                ep_text += f"   Kết quả: {ep['outcome']}\n"
            if ep.get('lesson_learned'):
                ep_text += f"   Bài học: {ep['lesson_learned']}\n"
        sections.append(("episodes", ep_text))
    
    # 3. Semantic hits
    if semantic_hits:
        sem_text = "\n=== DOCUMENTS LIÊN QUAN ===\n"
        for i, hit in enumerate(semantic_hits[:2], 1):  # Max 2 docs
            text = hit["text"][:400]  # Truncate
            source = hit.get("metadata", {}).get("source", "Unknown")
            sem_text += f"\n{i}. [{source}]\n{text}...\n"
        sections.append(("semantic", sem_text))
    
    # 4. Recent conversation
    if recent_conversation:
        conv_text = f"\n=== HỘI THOẠI GẦN ĐÂY ===\n{recent_conversation}\n"
        sections.append(("conversation", conv_text))
    
    # Trim sections to fit budget
    total_text = "".join(text for _, text in sections)
    total_tokens = estimate_tokens(total_text)
    
    if total_tokens > memory_budget:
        # Trim each section proportionally
        ratio = memory_budget / total_tokens
        sections = [
            (name, trim_to_budget(text, int(estimate_tokens(text) * ratio)))
            for name, text in sections
        ]
    
    # Combine all memory sections
    memory_context = "\n".join(text for _, text in sections)
    if estimate_tokens(memory_context) > memory_budget:
        memory_context = trim_to_budget(memory_context, memory_budget)
    
    # Build final messages
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": memory_context},
        {"role": "user", "content": user_message}
    ]
    
    return messages
