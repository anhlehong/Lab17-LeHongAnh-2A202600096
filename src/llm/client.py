"""LLM Client wrapper for OpenAI-compatible API."""
import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import json
import time

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None

load_dotenv()


class LLMClient:
    """
    Wrapper cho LLM API (OpenAI-compatible).
    Chỉ gọi tuần tự (sequential) vì API không hỗ trợ concurrent requests.
    """
    
    def __init__(self):
        self.api_base = os.getenv("LLM_API_BASE")
        self.api_key = os.getenv("LLM_API_KEY")
        self.model = os.getenv("LLM_MODEL")
        
        if not all([self.api_base, self.api_key, self.model]):
            raise ValueError("Missing LLM configuration in .env file")
        
        # Initialize LangChain ChatOpenAI client
        if ChatOpenAI:
            self.client = ChatOpenAI(
                base_url=self.api_base.replace("/chat/completions", ""),
                api_key=self.api_key,
                model=self.model,
                temperature=0.7,
            )
        else:
            self.client = None
            print("Warning: langchain-openai not installed, using mock responses")
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Gọi LLM API với messages.
        
        Args:
            messages: List of {"role": "user/assistant/system", "content": "..."}
            temperature: Temperature for generation
            max_tokens: Max tokens to generate
            
        Returns:
            Response content string
        """
        if not self.client:
            # Mock response for testing without API
            return "Mock response: I understand your request."
        
        try:
            # Convert to LangChain message format
            from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
            
            lc_messages = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                if role == "system":
                    lc_messages.append(SystemMessage(content=content))
                elif role == "assistant":
                    lc_messages.append(AIMessage(content=content))
                else:
                    lc_messages.append(HumanMessage(content=content))
            
            # Call API (sequential only)
            response = self.client.invoke(lc_messages)
            return response.content
            
        except Exception as e:
            print(f"LLM API error: {e}")
            return f"Error: {str(e)}"
    
    def extract_facts(self, conversation: str, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract user facts từ conversation để update profile.
        Xử lý conflict: fact mới override fact cũ.
        
        Args:
            conversation: Recent conversation text
            user_profile: Current user profile
            
        Returns:
            Updated facts dict
        """
        prompt = f"""Phân tích đoạn hội thoại sau và trích xuất thông tin về user.

Hồ sơ hiện tại:
{json.dumps(user_profile, ensure_ascii=False, indent=2)}

Hội thoại:
{conversation}

Nhiệm vụ:
1. Trích xuất các facts mới về user (tên, sở thích, dị ứng, công việc, v.v.)
2. Nếu có fact mới mâu thuẫn với fact cũ, ưu tiên fact mới (user đã sửa)
3. Trả về JSON với các facts cần update

Ví dụ:
- "Tôi tên là Linh" → {{"name": "Linh"}}
- "Tôi dị ứng sữa bò" → {{"allergy": "sữa bò"}}
- "À nhầm, tôi dị ứng đậu nành" → {{"allergy": "đậu nành"}} (override fact cũ)

Chỉ trả về JSON, không giải thích:"""

        messages = [
            {"role": "system", "content": "Bạn là trợ lý trích xuất thông tin user. Chỉ trả về JSON."},
            {"role": "user", "content": prompt}
        ]
        
        response = self.chat(messages, temperature=0.3)
        
        try:
            # Parse JSON từ response
            # Tìm JSON block trong response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()
            
            facts = json.loads(json_str)
            return facts if isinstance(facts, dict) else {}
        except Exception as e:
            print(f"Failed to parse facts: {e}")
            return {}
    
    def should_save_episode(self, conversation: str) -> tuple[bool, Optional[Dict[str, Any]]]:
        """
        Kiểm tra xem có nên lưu episode không (task hoàn tất, outcome rõ).
        
        Args:
            conversation: Recent conversation text
            
        Returns:
            (should_save, episode_data)
        """
        prompt = f"""Phân tích đoạn hội thoại sau và xác định xem có task/episode nào hoàn tất không.

Hội thoại:
{conversation}

Nhiệm vụ:
1. Xác định có task/episode hoàn tất không (vd: debug xong, học được bài học, giải quyết vấn đề)
2. Nếu có, trích xuất: title, outcome, lesson_learned
3. Trả về JSON

Ví dụ:
- "Đã fix lỗi docker bằng cách dùng service name" → {{"should_save": true, "title": "Fix docker connection", "outcome": "Dùng service name thay vì localhost", "lesson_learned": "Docker networking cần dùng service name"}}
- "Tôi tên là Linh" → {{"should_save": false}}

Chỉ trả về JSON:"""

        messages = [
            {"role": "system", "content": "Bạn là trợ lý phân tích episode. Chỉ trả về JSON."},
            {"role": "user", "content": prompt}
        ]
        
        response = self.chat(messages, temperature=0.3)
        
        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()
            
            result = json.loads(json_str)
            should_save = result.get("should_save", False)
            
            if should_save:
                episode = {
                    "title": result.get("title", "Unknown task"),
                    "outcome": result.get("outcome", ""),
                    "lesson_learned": result.get("lesson_learned", ""),
                    "timestamp": time.time()
                }
                return True, episode
            return False, None
        except Exception as e:
            print(f"Failed to parse episode: {e}")
            return False, None
