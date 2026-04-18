"""
NEXUS Memory Module — Persistent Interaction Log & Adaptive Learning
Records all interactions, maintains priority cache, and supports RL-inspired feedback.
"""

import json
import os
import time
from datetime import datetime
from collections import Counter


class Memory:
    """Persistent memory system with interaction logging, priority cache, and adaptive learning."""

    def __init__(self, config_path="config.json"):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config = self._load_config(config_path)

        # Memory file path
        memory_path = self.config.get("paths", {}).get("memory_log", "data/memory_log.json")
        self.memory_file = os.path.join(self.base_dir, memory_path)

        # Load existing memory
        self.memory = self._load_memory()

        # In-session priority cache (frequent commands get faster processing)
        self.priority_cache = self.memory.get("priority_cache", {})

        # Session start time
        self.session_start = time.time()
        self.session_interaction_count = 0

    def _load_config(self, config_path):
        """Load config."""
        full_path = os.path.join(self.base_dir, config_path)
        try:
            with open(full_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def _load_memory(self):
        """Load memory log from disk."""
        try:
            with open(self.memory_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {"interactions": [], "priority_cache": {}, "corrections": []}

    def _save_memory(self):
        """Save memory log to disk."""
        try:
            os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
            self.memory["priority_cache"] = self.priority_cache
            with open(self.memory_file, "w") as f:
                json.dump(self.memory, f, indent=4)
        except Exception as e:
            print(f"[MEMORY] Save error: {e}")

    def log_interaction(self, command, intent, action_taken, response, success=True):
        """
        Log a user interaction.
        Records command, intent, action, response, and success status.
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "command": command,
            "intent": intent,
            "action_taken": action_taken,
            "response": response,
            "success": success,
            "session_id": str(int(self.session_start))
        }

        self.memory["interactions"].append(entry)
        self.session_interaction_count += 1

        # Update priority cache
        self._update_priority_cache(command, intent)

        # Keep memory manageable (last 500 interactions)
        if len(self.memory["interactions"]) > 500:
            self.memory["interactions"] = self.memory["interactions"][-500:]

        # Save periodically (every 5 interactions)
        if self.session_interaction_count % 5 == 0:
            self._save_memory()

    def log_correction(self, original_command, corrected_intent, feedback=None):
        """
        Log a user correction for adaptive learning.
        When the user corrects the system, the NLU can learn from this.
        """
        correction = {
            "timestamp": datetime.now().isoformat(),
            "original_command": original_command,
            "corrected_intent": corrected_intent,
            "feedback": feedback
        }

        self.memory.setdefault("corrections", []).append(correction)
        self._save_memory()

        return "Correction logged. I'll learn from this."

    def _update_priority_cache(self, command, intent):
        """Update frequency-based priority cache."""
        # Create a simplified key from the command
        key = f"{intent}:{self._simplify_command(command)}"

        if key in self.priority_cache:
            self.priority_cache[key]["count"] += 1
            self.priority_cache[key]["last_used"] = datetime.now().isoformat()
        else:
            self.priority_cache[key] = {
                "count": 1,
                "intent": intent,
                "command_pattern": self._simplify_command(command),
                "last_used": datetime.now().isoformat()
            }

    def _simplify_command(self, command):
        """Simplify a command to its pattern for caching."""
        if not command:
            return ""
        words = command.lower().split()
        # Keep first 3 words as the pattern
        return " ".join(words[:3])

    def get_frequent_commands(self, top_n=10):
        """Get the most frequently used commands."""
        sorted_cache = sorted(
            self.priority_cache.items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )
        return sorted_cache[:top_n]

    def is_high_priority(self, command, intent):
        """Check if a command is in the priority cache (for faster processing)."""
        key = f"{intent}:{self._simplify_command(command)}"
        entry = self.priority_cache.get(key)
        return entry is not None and entry.get("count", 0) >= 3

    def get_corrections_for_intent(self, intent):
        """Get all corrections made for a specific intent."""
        corrections = self.memory.get("corrections", [])
        return [c for c in corrections if c.get("corrected_intent") == intent]

    def get_session_stats(self):
        """Get current session statistics."""
        elapsed = time.time() - self.session_start
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        seconds = int(elapsed % 60)

        return {
            "session_duration": f"{hours:02d}:{minutes:02d}:{seconds:02d}",
            "interactions_this_session": self.session_interaction_count,
            "total_interactions": len(self.memory.get("interactions", [])),
            "total_corrections": len(self.memory.get("corrections", [])),
            "cached_patterns": len(self.priority_cache)
        }

    def get_recent_interactions(self, n=5):
        """Get the N most recent interactions."""
        interactions = self.memory.get("interactions", [])
        return interactions[-n:] if interactions else []

    def clear_memory(self):
        """Clear all stored memory."""
        self.memory = {"interactions": [], "priority_cache": {}, "corrections": []}
        self.priority_cache = {}
        self._save_memory()
        return "Memory cleared successfully."

    def export_memory(self, export_path=None):
        """Export memory to a file."""
        if not export_path:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            export_dir = os.path.join(self.base_dir, "data", "exports")
            os.makedirs(export_dir, exist_ok=True)
            export_path = os.path.join(export_dir, f"memory_export_{timestamp}.json")

        try:
            self._save_memory()  # Ensure latest data is saved
            with open(self.memory_file, "r") as src:
                data = json.load(src)
            with open(export_path, "w") as dst:
                json.dump(data, dst, indent=4)
            return f"Memory exported to {export_path}."
        except Exception as e:
            return f"Export failed: {e}"

    def flush(self):
        """Force save all memory to disk."""
        self._save_memory()
        return "Memory flushed to disk."


# Convenience singleton
_instance = None

def get_memory(config_path="config.json"):
    """Get or create a singleton Memory instance."""
    global _instance
    if _instance is None:
        _instance = Memory(config_path)
    return _instance
