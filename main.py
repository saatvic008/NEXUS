"""
NEXUS — Main Orchestrator
Initializes all modules, runs the two-phase listen loop:
wake word → auth → command → NLU → dispatch → execute → respond → loop
Manages HUD on a separate thread.
"""

import os
import sys
import time
import threading
import signal

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from core.tts import get_tts
from core.listener import get_listener
from core.auth import get_auth
from core.nlu import get_nlu, NLU
from core.executor import get_executor
from core.browser import get_browser
from core.qa import get_qa
from core.decision_engine import get_decision_engine
from core.memory import get_memory
from core.hud import get_hud


class NEXUS:
    """Main NEXUS orchestrator — the brain that connects everything."""

    VERSION = "1.0.0"

    def __init__(self):
        print(r"""
    ╔══════════════════════════════════════════════╗
    ║                                              ║
    ║     ███╗   ██╗███████╗██╗  ██╗██╗   ██╗███████╗    ║
    ║     ████╗  ██║██╔════╝╚██╗██╔╝██║   ██║██╔════╝    ║
    ║     ██╔██╗ ██║█████╗   ╚███╔╝ ██║   ██║███████╗    ║
    ║     ██║╚██╗██║██╔══╝   ██╔██╗ ██║   ██║╚════██║    ║
    ║     ██║ ╚████║███████╗██╔╝ ██╗╚██████╔╝███████║    ║
    ║     ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝    ║
    ║                                              ║
    ║   Intelligent Voice-Activated Assistant v{self.VERSION}    ║
    ╚══════════════════════════════════════════════╝
        """)

        # Initialize all modules
        print("[NEXUS] Initializing modules...")
        self.tts = get_tts()
        self.listener = get_listener()
        self.auth = get_auth()
        self.nlu = get_nlu()
        self.executor = get_executor()
        self.browser = get_browser()
        self.qa = get_qa()
        self.decision_engine = get_decision_engine()
        self.memory = get_memory()
        self.hud = get_hud()

        # State
        self.running = False
        self.session_start = time.time()

        # Register signal handlers for clean shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        print("[NEXUS] All modules initialized ✓")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print("\n[NEXUS] Shutting down...")
        self.stop()

    def start(self):
        """Start NEXUS — the main run loop."""
        self.running = True

        # Start HUD
        self.hud.start()
        self.hud.update_status("locked")

        # Check if passkey is configured
        if not self.auth.is_passkey_configured():
            print("[NEXUS] No passkey configured. Starting onboarding...")
            self._run_onboarding()

        # Main loop
        print("[NEXUS] System active. Listening for wake word...")
        self.tts.speak(f"NEXUS system active. Say your wake word to begin.")

        while self.running:
            try:
                self._main_loop()
            except KeyboardInterrupt:
                print("\n[NEXUS] Interrupted by user.")
                break
            except Exception as e:
                print(f"[NEXUS] Error in main loop: {e}")
                time.sleep(1)

        self.stop()

    def _main_loop(self):
        """Single iteration of the main loop."""
        # Update HUD stats
        self._update_hud_stats()

        # Check idle timeout
        if self.auth.is_unlocked and self.auth.check_idle_timeout():
            self.hud.update_status("locked")
            self.tts.speak("System locked due to inactivity.")

        if not self.auth.is_unlocked:
            # Phase 1: Listen for wake word
            self.hud.update_status("listening")
            wake_detected = self.listener.listen_for_wake_word()

            if wake_detected:
                self.hud.update_status("processing")
                self.tts.speak("Wake word detected. Please speak your passkey.")

                # Phase 2: Authenticate
                passkey_phrase = self.listener.listen_for_passkey()
                if passkey_phrase:
                    if self.auth.verify_passkey(passkey_phrase):
                        self.hud.update_status("idle")
                        self.tts.speak("Welcome back. System unlocked. How can I help you?")
                    else:
                        status = self.auth.get_status()
                        if status["locked_out"]:
                            self.tts.speak(f"Too many failed attempts. Locked for {status['lockout_remaining']} seconds.")
                        else:
                            self.tts.speak("Incorrect passkey. Please try again.")
                        self.hud.update_status("locked")
        else:
            # System is unlocked — listen for commands
            self.hud.update_status("listening")
            command = self.listener.listen_for_command()

            if command:
                self.auth.refresh_activity()
                self.hud.update_command(command)
                self.hud.update_status("processing")

                # Process the command
                response = self._process_command(command)

                # Respond
                self.hud.update_response(response)
                self.hud.update_status("speaking")
                self.tts.speak(response)
                self.hud.update_status("idle")

    def _process_command(self, command):
        """Process a voice command through NLU and dispatch to handler."""
        # Check for system commands first
        command_lower = command.lower().strip()

        # Exit commands
        if command_lower in ("exit", "quit", "stop", "goodbye", "shut down nexus"):
            self.tts.speak("Goodbye. Shutting down NEXUS.")
            self.running = False
            return "Shutting down."

        # Lock command
        if command_lower in ("lock", "lock yourself", "lock system"):
            self.auth.lock()
            self.hud.update_status("locked")
            return "System locked."

        # HUD toggle
        if "hide hud" in command_lower or "hide display" in command_lower:
            self.hud.hide()
            return "Display hidden."
        if "show hud" in command_lower or "show display" in command_lower:
            self.hud.show()
            return "Display shown."

        # Memory commands
        if "clear memory" in command_lower:
            result = self.memory.clear_memory()
            return result
        if "export memory" in command_lower:
            result = self.memory.export_memory()
            return result

        # NLU classification
        result = self.nlu.classify(command)
        intent = result["intent"]
        confidence = result["confidence"]
        entities = result["entities"]

        print(f"[NEXUS] Intent: {intent} (confidence: {confidence:.2f})")

        # Check if clarification needed
        if result.get("needs_clarification"):
            prompt = self.nlu.get_clarification_prompt(result)
            self.tts.speak(prompt)
            # Listen for clarification
            clarification = self.listener.listen_for_command()
            if clarification:
                # Re-classify with additional context
                combined = f"{command} {clarification}"
                result = self.nlu.classify(combined)
                intent = result["intent"]
                entities = result["entities"]

        # Dispatch to appropriate handler
        response = self._dispatch(intent, entities, command)

        # Log interaction
        self.memory.log_interaction(command, intent, str(entities), response)

        return response

    def _dispatch(self, intent, entities, original_command):
        """Dispatch to the appropriate handler based on intent."""
        try:
            if intent == NLU.INTENT_SYSTEM:
                return self.executor.execute(entities)

            elif intent == NLU.INTENT_BROWSER:
                return self.browser.execute(entities)

            elif intent == NLU.INTENT_QA:
                return self.qa.answer(entities)

            elif intent == NLU.INTENT_SIMULATION:
                result = self.decision_engine.decide(entities)
                if result.get("chart_path"):
                    print(f"[NEXUS] Decision chart saved: {result['chart_path']}")
                return result.get("spoken", "I couldn't complete the simulation.")

            elif intent == NLU.INTENT_CONFIG:
                return self._handle_config(entities, original_command)

            else:
                return "I'm not sure how to help with that. Could you rephrase?"

        except Exception as e:
            print(f"[NEXUS] Dispatch error: {e}")
            return f"Sorry, something went wrong: {e}"

    def _handle_config(self, entities, command):
        """Handle system configuration commands."""
        setting = entities.get("setting", "").lower()
        value = entities.get("value", "")

        if "passkey" in setting:
            self.tts.speak("To change your passkey, please speak your current passkey.")
            old = self.listener.listen_for_passkey()
            if old:
                self.tts.speak("Now speak your new passkey.")
                new = self.listener.listen_for_passkey()
                if new:
                    if self.auth.change_passkey(old, new):
                        return "Passkey changed successfully."
                    return "Failed to change passkey. Old passkey incorrect."
            return "Passkey change cancelled."

        elif "volume" in setting or "speed" in setting or "rate" in setting:
            if value:
                try:
                    numeric = int(value)
                    if "volume" in setting:
                        self.tts.set_volume(numeric / 100)
                        return f"Volume set to {numeric}%."
                    else:
                        self.tts.set_rate(numeric)
                        return f"Speech rate set to {numeric}."
                except ValueError:
                    return "Please specify a number."
            return f"Current {setting}: use 'set {setting} to [value]' to change."

        elif "voice" in setting:
            voices = self.tts.get_available_voices()
            if voices:
                voice_list = ", ".join([f"{v['index']}: {v['name']}" for v in voices])
                return f"Available voices: {voice_list}."
            return "No voices available."

        else:
            stats = self.memory.get_session_stats()
            return (f"Session duration: {stats['session_duration']}. "
                    f"Total interactions: {stats['total_interactions']}. "
                    f"Cached patterns: {stats['cached_patterns']}.")

    def _run_onboarding(self):
        """Run first-time setup for passkey configuration."""
        self.hud.update_status("processing")
        print("\n" + "=" * 50)
        print("  NEXUS — First-Time Setup")
        print("=" * 50)

        self.tts.speak("Welcome to NEXUS. Let's set up your voice passkey. "
                      "Please speak a phrase that will be your secret passkey. "
                      "This can be any combination of words.")

        passkey_phrase = self.listener.listen_for_passkey()
        if passkey_phrase:
            self.tts.speak(f"I heard: {passkey_phrase}. Speak it again to confirm.")
            confirm = self.listener.listen_for_passkey()
            if confirm and confirm.lower().strip() == passkey_phrase.lower().strip():
                self.auth.setup_passkey(passkey_phrase)
                self.tts.speak("Passkey configured. You're all set. "
                              "Say the wake word followed by your passkey to unlock.")
            else:
                self.tts.speak("Passphrases didn't match. Please restart and try again.")
                # Allow keyboard fallback
                print("[NEXUS] Keyboard fallback: type your passkey below.")
                manual = input("Enter passkey: ").strip()
                if manual:
                    self.auth.setup_passkey(manual)
                    print("[NEXUS] Passkey configured via keyboard.")
        else:
            # Keyboard fallback
            print("[NEXUS] No speech detected. Using keyboard input.")
            manual = input("Enter passkey: ").strip()
            if manual:
                self.auth.setup_passkey(manual)
                print("[NEXUS] Passkey configured via keyboard.")

    def _update_hud_stats(self):
        """Update HUD with current session stats."""
        elapsed = time.time() - self.session_start
        h = int(elapsed // 3600)
        m = int((elapsed % 3600) // 60)
        s = int(elapsed % 60)
        duration = f"{h:02d}:{m:02d}:{s:02d}"
        self.hud.update_stats(duration, self.memory.session_interaction_count)

    def stop(self):
        """Stop NEXUS and all modules."""
        self.running = False
        self.memory.flush()
        self.hud.stop()
        self.tts.stop()
        print("[NEXUS] All systems stopped. Goodbye.")


def main():
    """Entry point for NEXUS."""
    nexus = NEXUS()
    nexus.start()


if __name__ == "__main__":
    main()
