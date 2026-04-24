"""Short-term memory: Sliding window conversation buffer."""
from typing import List, Dict, Any
from collections import deque


class ShortTermMemory:
    """
    Short-term memory lưu conversation gần đây.
    Sử dụng sliding window với max_messages.
    """
    
    def __init__(self, max_messages: int = 10):
        """
        Args:
            max_messages: Số lượng messages tối đa giữ lại
        """
        self.max_messages = max_messages
        self.buffer = deque(maxlen=max_messages)
    
    def add_message(self, role: str, content: str):
        """Thêm message vào buffer."""
        self.buffer.append({"role": role, "content": content})
    
    def get_messages(self) -> List[Dict[str, str]]:
        """Lấy tất cả messages trong buffer."""
        return list(self.buffer)
    
    def get_recent_text(self, num_messages: int = None) -> str:
        """
        Lấy text của N messages gần nhất.
        
        Args:
            num_messages: Số messages lấy (None = all)
            
        Returns:
            Formatted conversation text
        """
        messages = list(self.buffer)
        if num_messages:
            messages = messages[-num_messages:]
        
        lines = []
        for msg in messages:
            role = msg["role"].capitalize()
            content = msg["content"]
            lines.append(f"{role}: {content}")
        
        return "\n".join(lines)
    
    def clear(self):
        """Xóa toàn bộ buffer."""
        self.buffer.clear()
    
    def __len__(self):
        return len(self.buffer)
