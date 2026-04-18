"""
NEXUS TTS Module — Text-to-Speech Engine
Uses pyttsx3 for offline speech synthesis with configurable voice, rate, and volume.
"""

import json
import os
import threading
import queue

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False


class TextToSpeech:
    """Text-to-speech engine with queue support for non-blocking speech."""

    def __init__(self, config_path="config.json"):
        self.config = self._load_config(config_path)
        self.speech_queue = queue.Queue()
        self.is_speaking = False
        self._lock = threading.Lock()

        if TTS_AVAILABLE:
            self.engine = pyttsx3.init()
            self._configure_engine()
        else:
            self.engine = None
            print("[TTS] WARNING: pyttsx3 not installed. Speech output disabled.")

    def _load_config(self, config_path):
        """Load TTS configuration from config.json."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        full_path = os.path.join(base_dir, config_path)
        try:
            with open(full_path, "r") as f:
                config = json.load(f)
            return config.get("tts", {"rate": 175, "volume": 0.9, "voice_index": 0})
        except FileNotFoundError:
            return {"rate": 175, "volume": 0.9, "voice_index": 0}

    def _configure_engine(self):
        """Apply configuration to the TTS engine."""
        if not self.engine:
            return

        # Set speech rate
        self.engine.setProperty("rate", self.config.get("rate", 175))

        # Set volume (0.0 to 1.0)
        self.engine.setProperty("volume", self.config.get("volume", 0.9))

        # Set voice
        voices = self.engine.getProperty("voices")
        voice_index = self.config.get("voice_index", 0)
        if voices and 0 <= voice_index < len(voices):
            self.engine.setProperty("voice", voices[voice_index].id)

    def speak(self, text):
        """Speak text synchronously."""
        if not self.engine:
            print(f"[TTS] (no engine) {text}")
            return

        with self._lock:
            self.is_speaking = True
            try:
                self.engine.say(text)
                self.engine.runAndWait()
            except RuntimeError:
                # Engine may be busy; reinitialize
                self.engine = pyttsx3.init()
                self._configure_engine()
                self.engine.say(text)
                self.engine.runAndWait()
            finally:
                self.is_speaking = False

    def speak_async(self, text):
        """Queue text for asynchronous speech in a background thread."""
        self.speech_queue.put(text)
        thread = threading.Thread(target=self._process_queue, daemon=True)
        thread.start()

    def _process_queue(self):
        """Process queued speech items."""
        while not self.speech_queue.empty():
            text = self.speech_queue.get()
            self.speak(text)
            self.speech_queue.task_done()

    def get_available_voices(self):
        """Return list of available voice names."""
        if not self.engine:
            return []
        voices = self.engine.getProperty("voices")
        return [{"index": i, "name": v.name, "id": v.id} for i, v in enumerate(voices)]

    def set_rate(self, rate):
        """Dynamically change speech rate."""
        self.config["rate"] = rate
        if self.engine:
            self.engine.setProperty("rate", rate)

    def set_volume(self, volume):
        """Dynamically change speech volume (0.0 to 1.0)."""
        self.config["volume"] = max(0.0, min(1.0, volume))
        if self.engine:
            self.engine.setProperty("volume", self.config["volume"])

    def stop(self):
        """Stop any ongoing speech."""
        if self.engine:
            try:
                self.engine.stop()
            except Exception:
                pass
        self.is_speaking = False


# Convenience singleton
_instance = None

def get_tts(config_path="config.json"):
    """Get or create a singleton TTS instance."""
    global _instance
    if _instance is None:
        _instance = TextToSpeech(config_path)
    return _instance
