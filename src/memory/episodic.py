"""Episodic memory: Task/episode history storage."""
import json
import os
from typing import List, Dict, Any
from pathlib import Path


class EpisodicMemory:
    """
    Episodic memory lưu các episodes/tasks đã hoàn thành.
    Backend: JSON file.
    """
    
    def __init__(self, user_id: str, storage_dir: str = "data/episodes"):
        """
        Args:
            user_id: User identifier
            storage_dir: Directory to store episode files
        """
        self.user_id = user_id
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.file_path = self.storage_dir / f"{user_id}.json"
    
    def _load_episodes(self) -> List[Dict[str, Any]]:
        """Load episodes từ file."""
        if not self.file_path.exists():
            return []
        
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Failed to load episodes: {e}")
            return []
    
    def _save_episodes(self, episodes: List[Dict[str, Any]]):
        """Save episodes vào file."""
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(episodes, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to save episodes: {e}")
    
    def add_episode(self, episode: Dict[str, Any]):
        """
        Thêm episode mới.
        
        Args:
            episode: Dict chứa title, outcome, lesson_learned, timestamp
        """
        episodes = self._load_episodes()
        episodes.append(episode)
        self._save_episodes(episodes)
    
    def get_episodes(self, limit: int = None) -> List[Dict[str, Any]]:
        """
        Lấy episodes (mới nhất trước).
        
        Args:
            limit: Số lượng episodes tối đa (None = all)
            
        Returns:
            List of episodes
        """
        episodes = self._load_episodes()
        episodes.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        
        if limit:
            return episodes[:limit]
        return episodes
    
    def search_episodes(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Tìm kiếm episodes liên quan đến query (simple keyword search).
        
        Args:
            query: Search query
            limit: Max results
            
        Returns:
            List of relevant episodes
        """
        episodes = self._load_episodes()
        query_lower = query.lower()
        
        # Simple keyword matching
        scored_episodes = []
        for ep in episodes:
            score = 0
            text = f"{ep.get('title', '')} {ep.get('outcome', '')} {ep.get('lesson_learned', '')}".lower()
            
            # Count keyword matches
            for word in query_lower.split():
                if word in text:
                    score += 1
            
            if score > 0:
                scored_episodes.append((score, ep))
        
        # Sort by score
        scored_episodes.sort(key=lambda x: x[0], reverse=True)
        
        return [ep for _, ep in scored_episodes[:limit]]
    
    def clear(self):
        """Xóa toàn bộ episodes (GDPR compliance)."""
        if self.file_path.exists():
            self.file_path.unlink()
    
    def format_for_prompt(self, episodes: List[Dict[str, Any]]) -> str:
        """Format episodes thành text để inject vào prompt."""
        if not episodes:
            return "Chưa có episodes liên quan."
        
        lines = ["Các episodes/tasks trước đây:"]
        for i, ep in enumerate(episodes, 1):
            title = ep.get("title", "Unknown")
            outcome = ep.get("outcome", "")
            lesson = ep.get("lesson_learned", "")
            
            lines.append(f"\n{i}. {title}")
            if outcome:
                lines.append(f"   Kết quả: {outcome}")
            if lesson:
                lines.append(f"   Bài học: {lesson}")
        
        return "\n".join(lines)
