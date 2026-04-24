"""Token counting utilities."""
import tiktoken


def estimate_tokens(text: str, model: str = "gpt-4") -> int:
    """
    Ước lượng số tokens trong text.
    
    Args:
        text: Input text
        model: Model name (để chọn encoding)
        
    Returns:
        Estimated token count
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception:
        # Fallback: rough estimate (1 token ≈ 4 chars)
        return len(text) // 4


def trim_to_budget(text: str, budget: int, model: str = "gpt-4") -> str:
    """
    Trim text để fit vào token budget.
    
    Args:
        text: Input text
        budget: Max tokens
        model: Model name
        
    Returns:
        Trimmed text
    """
    tokens = estimate_tokens(text, model)
    
    if tokens <= budget:
        return text
    
    # Trim by ratio
    ratio = budget / tokens
    target_chars = int(len(text) * ratio * 0.9)  # 90% để an toàn
    
    return text[:target_chars] + "..."
