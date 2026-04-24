"""Unit tests for memory backends."""
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.memory import EpisodicMemory, ProfileMemory, SemanticMemory, ShortTermMemory


def test_short_term_memory():
    print("\n=== Test Short-term Memory ===")
    stm = ShortTermMemory(max_messages=3)

    stm.add_message("user", "Hello")
    stm.add_message("assistant", "Hi there!")
    stm.add_message("user", "How are you?")

    assert len(stm) == 3
    print("[OK] Added 3 messages")

    stm.add_message("assistant", "I'm good!")
    assert len(stm) == 3
    print("[OK] Sliding window works")

    text = stm.get_recent_text(num_messages=2)
    assert "How are you?" in text
    print("[OK] Get recent text works")

    stm.clear()
    assert len(stm) == 0
    print("[OK] Clear works")


def test_profile_memory():
    print("\n=== Test Profile Memory ===")
    profile = ProfileMemory(user_id="test_user", use_redis=False)
    profile.clear()

    profile.update_facts({"name": "Linh", "job": "developer"})
    data = profile.get_profile()
    assert data["name"] == "Linh"
    assert data["job"] == "developer"
    print("[OK] Update facts works")

    profile.update_facts({"job": "data scientist"})
    data = profile.get_profile()
    assert data["job"] == "data scientist"
    print("[OK] Conflict handling works")

    assert profile.get_fact("name") == "Linh"
    print("[OK] Get single fact works")

    profile.delete_fact("job")
    assert "job" not in profile.get_profile()
    print("[OK] Delete fact works")

    profile.clear()
    assert profile.get_profile() == {}
    print("[OK] Clear works")


def test_episodic_memory():
    print("\n=== Test Episodic Memory ===")
    episodic = EpisodicMemory(user_id="test_user")
    episodic.clear()

    episode1 = {
        "title": "Fix docker error",
        "outcome": "Used service name",
        "lesson_learned": "Docker needs service name",
        "timestamp": time.time(),
    }
    episodic.add_episode(episode1)

    episodes = episodic.get_episodes()
    assert len(episodes) == 1
    assert episodes[0]["title"] == "Fix docker error"
    print("[OK] Add episode works")

    episode2 = {
        "title": "Setup Redis",
        "outcome": "Used Docker Compose",
        "lesson_learned": "Docker Compose is easy",
        "timestamp": time.time() + 1,
    }
    episodic.add_episode(episode2)

    episodes = episodic.get_episodes()
    assert len(episodes) == 2
    print("[OK] Multiple episodes work")

    results = episodic.search_episodes("docker", limit=2)
    assert len(results) == 2
    print("[OK] Search episodes works")

    episodic.clear()
    assert episodic.get_episodes() == []
    print("[OK] Clear works")


def test_semantic_memory():
    print("\n=== Test Semantic Memory ===")
    semantic = SemanticMemory(collection_name=f"test_docs_{uuid.uuid4().hex}")

    docs = [
        {
            "id": "doc1",
            "text": "Python is a programming language",
            "metadata": {"source": "doc1.txt"},
        },
        {
            "id": "doc2",
            "text": "Docker is a containerization platform",
            "metadata": {"source": "doc2.txt"},
        },
    ]
    semantic.add_documents(docs)
    print("[OK] Add documents works")

    results = semantic.search("programming", top_k=1)
    assert len(results) > 0
    assert "Python" in results[0]["text"]
    print("[OK] Search works")

    results = semantic.search("container", top_k=1)
    assert len(results) > 0
    assert "Docker" in results[0]["text"]
    print("[OK] Search different query works")


def run_all_tests():
    print("=" * 60)
    print("Running Memory Backend Tests")
    print("=" * 60)

    test_short_term_memory()
    test_profile_memory()
    test_episodic_memory()
    test_semantic_memory()

    print("\n" + "=" * 60)
    print("[OK] All tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        run_all_tests()
    except Exception as exc:
        print(f"\n[FAIL] {exc}")
        raise
