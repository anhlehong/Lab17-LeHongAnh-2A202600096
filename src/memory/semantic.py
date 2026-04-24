"""Semantic memory: Vector search for documents/FAQs."""
import os
from typing import List, Dict, Any
from pathlib import Path

try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False


class SemanticMemory:
    """
    Semantic memory cho document/FAQ retrieval.
    Backend: ChromaDB (vector search) hoặc keyword search fallback.
    """
    
    def __init__(
        self,
        collection_name: str = "documents",
        persist_directory: str = "data/chroma"
    ):
        """
        Args:
            collection_name: Tên collection trong ChromaDB
            persist_directory: Directory lưu ChromaDB data
        """
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.client = None
        self.collection = None
        self.documents = []  # Fallback storage
        
        # Try to initialize ChromaDB
        if CHROMA_AVAILABLE:
            try:
                self.client = chromadb.PersistentClient(path=persist_directory)
                self.collection = self.client.get_or_create_collection(
                    name=collection_name
                )
                print(f"[OK] ChromaDB initialized: {collection_name}")
            except Exception as e:
                print(f"ChromaDB init failed: {e}, using keyword search fallback")
                self.client = None
    
    def add_documents(self, documents: List[Dict[str, str]]):
        """
        Thêm documents vào semantic memory.
        
        Args:
            documents: List of {"id": "...", "text": "...", "metadata": {...}}
        """
        if self.collection:
            try:
                ids = [doc["id"] for doc in documents]
                texts = [doc["text"] for doc in documents]
                metadatas = [doc.get("metadata", {}) for doc in documents]
                
                self.collection.upsert(
                    ids=ids,
                    documents=texts,
                    metadatas=metadatas
                )
            except Exception as e:
                print(f"ChromaDB add error: {e}")
        else:
            # Fallback: store in memory
            self.documents.extend(documents)
    
    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Tìm kiếm documents liên quan đến query.
        
        Args:
            query: Search query
            top_k: Số lượng results tối đa
            
        Returns:
            List of {"text": "...", "metadata": {...}, "score": ...}
        """
        if self.collection:
            try:
                results = self.collection.query(
                    query_texts=[query],
                    n_results=top_k
                )
                
                # Format results
                hits = []
                if results["documents"] and results["documents"][0]:
                    for i, doc in enumerate(results["documents"][0]):
                        hits.append({
                            "text": doc,
                            "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                            "score": 1.0 - results["distances"][0][i] if results["distances"] else 0.0
                        })
                return hits
            except Exception as e:
                print(f"ChromaDB search error: {e}")
                return []
        else:
            # Fallback: keyword search
            return self._keyword_search(query, top_k)
    
    def _keyword_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Simple keyword search fallback."""
        query_lower = query.lower()
        scored_docs = []
        
        for doc in self.documents:
            text = doc["text"].lower()
            score = sum(1 for word in query_lower.split() if word in text)
            
            if score > 0:
                scored_docs.append((score, doc))
        
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        
        return [
            {
                "text": doc["text"],
                "metadata": doc.get("metadata", {}),
                "score": score / len(query_lower.split())
            }
            for score, doc in scored_docs[:top_k]
        ]
    
    def load_from_directory(self, directory: str):
        """
        Load tất cả text files từ directory vào semantic memory.
        
        Args:
            directory: Path to directory chứa documents
        """
        dir_path = Path(directory)
        if not dir_path.exists():
            print(f"Directory not found: {directory}")
            return
        
        documents = []
        for file_path in dir_path.glob("*.txt"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
                
                documents.append({
                    "id": file_path.stem,
                    "text": text,
                    "metadata": {"source": str(file_path)}
                })
            except Exception as e:
                print(f"Failed to load {file_path}: {e}")
        
        if documents:
            self.add_documents(documents)
            print(f"[OK] Loaded {len(documents)} documents from {directory}")
    
    def format_for_prompt(self, hits: List[Dict[str, Any]]) -> str:
        """Format search results thành text để inject vào prompt."""
        if not hits:
            return "Không tìm thấy documents liên quan."
        
        lines = ["Documents liên quan:"]
        for i, hit in enumerate(hits, 1):
            text = hit["text"][:300]  # Truncate
            source = hit.get("metadata", {}).get("source", "Unknown")
            
            lines.append(f"\n{i}. [{source}]")
            lines.append(f"   {text}...")
        
        return "\n".join(lines)
