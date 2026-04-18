"""
NEXUS Listener Module — Wake Word Detection + Active Listening
Two-phase listening: passive wake-word detection (low-power) → active command capture.
Supports Google Speech-to-Text (online) and Vosk (offline).
"""

import json
import os
import time
import threading

try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False

try:
    from vosk import Model as VoskModel, KaldiRecognizer
    import pyaudio
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False


class Listener:
    """Two-phase voice listener: wake word detection + active command capture."""

    def __init__(self, config_path="config.json"):
        self.config = self._load_config(config_path)
        self.wake_word = self.config.get("wake_word", "hey nexus").lower()
        self.listener_config = self.config.get("listener", {})
        self.engine = self.listener_config.get("engine", "google")
        self.is_listening = False
        self.is_active = False
        self._calibrated = False
        self._wake_variants = {
            "hey nexus", "a nexus", "hey nexis",
            "henexus", "hey nexos", "nexus"
        }

        # Initialize speech recognizer
        if SR_AVAILABLE:
            self.recognizer = sr.Recognizer()
            self.recognizer.energy_threshold = self.listener_config.get("energy_threshold", 200)
            self.recognizer.pause_threshold = self.listener_config.get("pause_threshold", 0.6)
            self.recognizer.dynamic_energy_threshold = True  # Auto-adjust mic sensitivity

            # Allow selecting a specific mic via config (default = system default)
            mic_index = self.listener_config.get("mic_index", None)
            if mic_index is not None:
                self.microphone = sr.Microphone(device_index=mic_index)
                print(f"[LISTENER] Using microphone index {mic_index}")
            else:
                self.microphone = sr.Microphone()
                print("[LISTENER] Using default microphone")

            # Show available mics for debugging
            print("[LISTENER] Available microphones:")
            for i, name in enumerate(sr.Microphone.list_microphone_names()):
                marker = " <-- SELECTED" if i == mic_index else ""
                print(f"  [{i}] {name}{marker}")
        else:
            self.recognizer = None
            self.microphone = None
            print("[LISTENER] WARNING: SpeechRecognition not installed.")

        # Initialize Vosk if selected
        self.vosk_model = None
        if self.engine == "vosk" and VOSK_AVAILABLE:
            model_path = self.listener_config.get("vosk_model_path", "models/vosk-model-small-en-us")
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            full_model_path = os.path.join(base_dir, model_path)
            if os.path.exists(full_model_path):
                self.vosk_model = VoskModel(full_model_path)
            else:
                print(f"[LISTENER] Vosk model not found at {full_model_path}. Falling back to Google.")
                self.engine = "google"

    def _load_config(self, config_path):
        """Load configuration from config.json."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        full_path = os.path.join(base_dir, config_path)
        try:
            with open(full_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {"wake_word": "hey nexus", "listener": {}}

    def _recognize_speech(self, audio):
        """Recognize speech from audio using the configured engine."""
        try:
            if self.engine == "vosk" and self.vosk_model:
                return self._recognize_vosk(audio)
            else:
                return self._recognize_google(audio)
        except Exception as e:
            print(f"[LISTENER] Recognition error: {e}")
            return None

    def _recognize_google(self, audio):
        """Recognize speech using Google Speech-to-Text API."""
        try:
            text = self.recognizer.recognize_google(audio)
            return text.lower().strip()
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            print(f"[LISTENER] Google STT request error: {e}")
            return None

    def _recognize_vosk(self, audio):
        """Recognize speech using Vosk offline engine."""
        try:
            recognizer = KaldiRecognizer(self.vosk_model, 16000)
            raw_data = audio.get_raw_data(convert_rate=16000, convert_width=2)
            recognizer.AcceptWaveform(raw_data)
            result = json.loads(recognizer.FinalResult())
            text = result.get("text", "")
            return text.lower().strip() if text else None
        except Exception as e:
            print(f"[LISTENER] Vosk recognition error: {e}")
            return None

    def listen_for_wake_word(self):
        """
        Phase 1: Passive wake word detection.
        Optimized for speed: calibrates mic once, uses local Vosk engine,
        no timeout (waits for speech), and fuzzy matching for reliability.
        Returns True when wake word is detected.
        """
        if not self.recognizer or not self.microphone:
            print("[LISTENER] No recognizer available. Simulating wake word detection.")
            user_input = input("[LISTENER] Type wake word or command: ").lower().strip()
            return self._fuzzy_wake_match(user_input)

        self.is_listening = True

        try:
            with self.microphone as source:
                # Calibrate ONCE on first call (longer duration for accurate noise floor)
                if not self._calibrated:
                    print("[LISTENER] Calibrating microphone... please wait.")
                    self.recognizer.adjust_for_ambient_noise(source, duration=2.0)
                    print(f"[LISTENER] Calibration done. Threshold: {self.recognizer.energy_threshold:.0f}")
                    self._calibrated = True

                print(f"[LISTENER] Say '{self.wake_word}' to activate...")
                # No timeout — waits patiently until user speaks
                audio = self.recognizer.listen(
                    source,
                    phrase_time_limit=4  # Wake words are short
                )

            print("[LISTENER] Audio captured, recognizing...")

            # Use local Vosk if available (no network latency) — fall back to configured engine
            if self.vosk_model:
                text = self._recognize_vosk(audio)
            else:
                text = self._recognize_speech(audio)

            print(f"[LISTENER] Heard: '{text}'")

            if text and self._fuzzy_wake_match(text):
                print(f"[LISTENER] ✓ Wake word matched!")
                self.is_listening = False
                return True
            elif text:
                print(f"[LISTENER] ✗ Not the wake word. Heard: '{text}'")

        except sr.WaitTimeoutError:
            print("[LISTENER] No speech detected, retrying...")
        except Exception as e:
            print(f"[LISTENER] Wake word listen error: {e}")

        self.is_listening = False
        return False

    def _fuzzy_wake_match(self, text):
        """Fast fuzzy matching — tolerates common STT misrecognitions of the wake word."""
        text = text.lower().strip()
        if self.wake_word in text:
            return True
        return any(variant in text for variant in self._wake_variants)

    def listen_for_command(self):
        """
        Phase 2: Active command capture.
        Listens for a full command after wake word / auth.
        No timeout — waits until user speaks.
        Returns the recognized command text or None.
        """
        if not self.recognizer or not self.microphone:
            # Fallback: keyboard input for testing
            user_input = input("[LISTENER] Enter command: ").strip()
            return user_input if user_input else None

        self.is_active = True
        print("[LISTENER] Listening for command... speak now.")

        try:
            with self.microphone as source:
                # No timeout — wait patiently for user to speak
                audio = self.recognizer.listen(
                    source,
                    phrase_time_limit=8  # Allow longer commands
                )

            print("[LISTENER] Audio captured, recognizing...")
            text = self._recognize_speech(audio)
            if text:
                print(f"[LISTENER] Command recognized: '{text}'")
                self.is_active = False
                return text
            else:
                print("[LISTENER] Could not understand. Please try again.")

        except sr.WaitTimeoutError:
            print("[LISTENER] No command detected (timeout).")
        except Exception as e:
            print(f"[LISTENER] Command listen error: {e}")

        self.is_active = False
        return None

    def listen_for_passkey(self):
        """
        Listen specifically for passkey input.
        Returns the recognized phrase for auth verification.
        """
        if not self.recognizer or not self.microphone:
            # Fallback: keyboard input for testing
            user_input = input("[AUTH] Speak your passkey: ").strip()
            return user_input if user_input else None

        print("[LISTENER] Listening for passkey... speak now.")

        try:
            with self.microphone as source:
                # No timeout — wait for user to speak passkey
                audio = self.recognizer.listen(
                    source,
                    phrase_time_limit=8  # Passkeys can be longer phrases
                )

            print("[LISTENER] Passkey audio captured, recognizing...")
            text = self._recognize_speech(audio)
            if text:
                print(f"[LISTENER] Passkey phrase captured: '{text}'")
                return text
            else:
                print("[LISTENER] Could not understand passkey. Try again.")

        except sr.WaitTimeoutError:
            print("[LISTENER] No passkey detected (timeout).")
        except Exception as e:
            print(f"[LISTENER] Passkey listen error: {e}")

        return None

    def calibrate(self):
        """Calibrate microphone for ambient noise levels."""
        if not self.recognizer or not self.microphone:
            print("[LISTENER] Cannot calibrate — no microphone available.")
            return

        print("[LISTENER] Calibrating microphone for ambient noise... Please be quiet.")
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
            print(f"[LISTENER] Calibration complete. Energy threshold: {self.recognizer.energy_threshold}")
        except Exception as e:
            print(f"[LISTENER] Calibration error: {e}")


# Convenience singleton
_instance = None

def get_listener(config_path="config.json"):
    """Get or create a singleton Listener instance."""
    global _instance
    if _instance is None:
        _instance = Listener(config_path)
    return _instance
