"""Long-term profile memory: User facts storage."""
import json
import os
from typing import Dict, Any, Optional

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class ProfileMemory:
    """
    Long-term profile memory lưu user facts.
    Backend: Redis (nếu có) hoặc dict fallback.
    """
    
    def __init__(self, user_id: str, use_redis: bool = True):
        """
        Args:
            user_id: User identifier
            use_redis: Có dùng Redis không (fallback to dict nếu không có)
        """
        self.user_id = user_id
        self.redis_client = None
        self.local_store = {}
        
        # Try to connect to Redis
        if use_redis and REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(
                    host=os.getenv("REDIS_HOST", "localhost"),
                    port=int(os.getenv("REDIS_PORT", "6379")),
                    db=0,
                    decode_responses=True
                )
                # Test connection
                self.redis_client.ping()
                print(f"[OK] Connected to Redis for user {user_id}")
            except Exception as e:
                print(f"Redis connection failed: {e}, using dict fallback")
                self.redis_client = None
    
    def _get_key(self) -> str:
        """Get Redis key for this user."""
        return f"profile:{self.user_id}"
    
    def get_profile(self) -> Dict[str, Any]:
        """Lấy toàn bộ profile của user."""
        if self.redis_client:
            try:
                data = self.redis_client.get(self._get_key())
                if data:
                    return json.loads(data)
                return {}
            except Exception as e:
                print(f"Redis get error: {e}")
                return {}
        else:
            return self.local_store.copy()
    
    def update_facts(self, facts: Dict[str, Any]):
        """
        Update profile với facts mới.
        Facts mới sẽ override facts cũ (conflict handling).
        
        Args:
            facts: Dict of facts to update
        """
        profile = self.get_profile()
        profile.update(facts)
        
        if self.redis_client:
            try:
                self.redis_client.set(
                    self._get_key(),
                    json.dumps(profile, ensure_ascii=False)
                )
            except Exception as e:
                print(f"Redis set error: {e}")
        else:
            self.local_store = profile
    
    def get_fact(self, key: str) -> Optional[Any]:
        """Lấy một fact cụ thể."""
        profile = self.get_profile()
        return profile.get(key)
    
    def delete_fact(self, key: str):
        """Xóa một fact (privacy/GDPR compliance)."""
        profile = self.get_profile()
        if key in profile:
            del profile[key]
            
            if self.redis_client:
                try:
                    self.redis_client.set(
                        self._get_key(),
                        json.dumps(profile, ensure_ascii=False)
                    )
                except Exception as e:
                    print(f"Redis set error: {e}")
            else:
                self.local_store = profile
    
    def clear(self):
        """Xóa toàn bộ profile (GDPR right to be forgotten)."""
        if self.redis_client:
            try:
                self.redis_client.delete(self._get_key())
            except Exception as e:
                print(f"Redis delete error: {e}")
        else:
            self.local_store.clear()
    
    def format_for_prompt(self) -> str:
        """Format profile thành text để inject vào prompt."""
        profile = self.get_profile()
        if not profile:
            return "Chưa có thông tin về user."
        
        lines = ["Thông tin về user:"]
        for key, value in profile.items():
            lines.append(f"- {key}: {value}")
        
        return "\n".join(lines)
