"""
Tests for NEXUS Memory Module — Interaction logging, priority cache, export/clear.
"""

import os
import sys
import json
import pytest
import tempfile
import shutil
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.memory import Memory


@pytest.fixture
def temp_memory():
    """Create a Memory instance with temporary storage."""
    temp_dir = tempfile.mkdtemp()

    # Create config
    data_dir = os.path.join(temp_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    config = {
        "paths": {"memory_log": "data/memory_log.json"}
    }
    config_path = os.path.join(temp_dir, "config.json")
    with open(config_path, "w") as f:
        json.dump(config, f)

    # Create empty memory log
    memory_data = {"interactions": [], "priority_cache": {}, "corrections": []}
    memory_path = os.path.join(data_dir, "memory_log.json")
    with open(memory_path, "w") as f:
        json.dump(memory_data, f)

    # Create Memory manually
    mem = Memory.__new__(Memory)
    mem.base_dir = temp_dir
    mem.config = config
    mem.memory_file = memory_path
    mem.memory = memory_data
    mem.priority_cache = {}
    mem.session_start = time.time()
    mem.session_interaction_count = 0

    yield mem, temp_dir

    shutil.rmtree(temp_dir)


class TestInteractionLogging:
    """Test interaction logging functionality."""

    def test_log_interaction(self, temp_memory):
        mem, _ = temp_memory
        mem.log_interaction("open notepad", "system_execution", "launch notepad", "Opening notepad.")
        assert len(mem.memory["interactions"]) == 1

    def test_log_structure(self, temp_memory):
        mem, _ = temp_memory
        mem.log_interaction("test command", "test_intent", "test_action", "test_response")
        entry = mem.memory["interactions"][0]
        assert "timestamp" in entry
        assert entry["command"] == "test command"
        assert entry["intent"] == "test_intent"
        assert entry["action_taken"] == "test_action"
        assert entry["response"] == "test_response"
        assert entry["success"] is True

    def test_log_failure(self, temp_memory):
        mem, _ = temp_memory
        mem.log_interaction("bad command", "unknown", "none", "Error", success=False)
        entry = mem.memory["interactions"][0]
        assert entry["success"] is False

    def test_session_counter(self, temp_memory):
        mem, _ = temp_memory
        mem.log_interaction("cmd1", "intent1", "act1", "resp1")
        mem.log_interaction("cmd2", "intent2", "act2", "resp2")
        assert mem.session_interaction_count == 2

    def test_memory_limit(self, temp_memory):
        mem, _ = temp_memory
        # Add 510 interactions
        for i in range(510):
            mem.memory["interactions"].append({
                "timestamp": "2024-01-01",
                "command": f"command {i}",
                "intent": "test",
                "action_taken": "test",
                "response": "test",
                "success": True
            })
        mem.log_interaction("latest", "test", "test", "test")
        assert len(mem.memory["interactions"]) <= 501  # 500 + 1 new


class TestPriorityCache:
    """Test priority cache functionality."""

    def test_cache_update(self, temp_memory):
        mem, _ = temp_memory
        mem.log_interaction("open notepad", "system_execution", "launch", "Done")
        assert len(mem.priority_cache) == 1

    def test_cache_frequency(self, temp_memory):
        mem, _ = temp_memory
        # Log same command multiple times
        for _ in range(5):
            mem.log_interaction("open notepad", "system_execution", "launch", "Done")
        # Check frequency in cache
        found = False
        for key, value in mem.priority_cache.items():
            if value["count"] >= 5:
                found = True
        assert found

    def test_high_priority_detection(self, temp_memory):
        mem, _ = temp_memory
        # Not high priority initially
        assert mem.is_high_priority("open notepad", "system_execution") is False

        # Log enough times
        for _ in range(5):
            mem.log_interaction("open notepad", "system_execution", "launch", "Done")

        assert mem.is_high_priority("open notepad", "system_execution") is True

    def test_frequent_commands(self, temp_memory):
        mem, _ = temp_memory
        for _ in range(10):
            mem.log_interaction("open notepad", "system_execution", "launch", "Done")
        for _ in range(5):
            mem.log_interaction("open chrome", "browser_control", "launch", "Done")

        frequent = mem.get_frequent_commands(top_n=2)
        assert len(frequent) == 2
        # Most frequent should be first
        assert frequent[0][1]["count"] >= frequent[1][1]["count"]


class TestCorrections:
    """Test correction logging and retrieval."""

    def test_log_correction(self, temp_memory):
        mem, _ = temp_memory
        result = mem.log_correction("open the browser", "browser_control", "User corrected from system_execution")
        assert "correction logged" in result.lower()
        assert len(mem.memory["corrections"]) == 1

    def test_get_corrections(self, temp_memory):
        mem, _ = temp_memory
        mem.log_correction("cmd1", "system_execution")
        mem.log_correction("cmd2", "browser_control")
        mem.log_correction("cmd3", "system_execution")

        system_corrections = mem.get_corrections_for_intent("system_execution")
        assert len(system_corrections) == 2


class TestSessionStats:
    """Test session statistics."""

    def test_stats_structure(self, temp_memory):
        mem, _ = temp_memory
        stats = mem.get_session_stats()
        assert "session_duration" in stats
        assert "interactions_this_session" in stats
        assert "total_interactions" in stats
        assert "total_corrections" in stats
        assert "cached_patterns" in stats

    def test_stats_values(self, temp_memory):
        mem, _ = temp_memory
        mem.log_interaction("test", "test", "test", "test")
        stats = mem.get_session_stats()
        assert stats["interactions_this_session"] == 1
        assert stats["total_interactions"] == 1


class TestRecentInteractions:
    """Test recent interaction retrieval."""

    def test_get_recent(self, temp_memory):
        mem, _ = temp_memory
        for i in range(10):
            mem.log_interaction(f"cmd{i}", "intent", "action", "response")
        recent = mem.get_recent_interactions(n=5)
        assert len(recent) == 5


class TestMemoryManagement:
    """Test memory clearing and exporting."""

    def test_clear_memory(self, temp_memory):
        mem, _ = temp_memory
        mem.log_interaction("test", "test", "test", "test")
        result = mem.clear_memory()
        assert "cleared" in result.lower()
        assert len(mem.memory["interactions"]) == 0
        assert len(mem.priority_cache) == 0

    def test_export_memory(self, temp_memory):
        mem, temp_dir = temp_memory
        mem.log_interaction("test", "test", "test", "test")
        mem.flush()  # Ensure data is saved
        result = mem.export_memory()
        assert "exported" in result.lower()

    def test_flush_memory(self, temp_memory):
        mem, temp_dir = temp_memory
        mem.log_interaction("test", "test", "test", "test")
        result = mem.flush()
        assert "flushed" in result.lower()

        # Verify file was written
        with open(mem.memory_file, "r") as f:
            data = json.load(f)
        assert len(data["interactions"]) == 1
