"""
NEXUS Auth Module — Voice Passkey Security System
SHA-256 hashed spoken passphrases with lockout logic, onboarding, and idle auto-lock.
"""

import hashlib
import json
import os
import time
from datetime import datetime


class Authenticator:
    """Voice passkey authentication with SHA-256 hashing and lockout protection."""

    def __init__(self, config_path="config.json"):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config_path = os.path.join(self.base_dir, config_path)
        self.config = self._load_config()

        # Auth state
        self.is_unlocked = False
        self.failed_attempts = 0
        self.lockout_until = 0
        self.last_activity_time = time.time()

        # Security config
        security = self.config.get("security", {})
        self.max_failed_attempts = security.get("max_failed_attempts", 3)
        self.lockout_duration = security.get("lockout_duration_seconds", 60)
        self.idle_timeout = security.get("idle_timeout_seconds", 300)
        self.log_failed = security.get("log_failed_attempts", True)

        # Failed attempt log
        self.attempt_log_path = os.path.join(self.base_dir, "data", "auth_log.json")

    def _load_config(self):
        """Load config from config.json."""
        try:
            with open(self.config_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {"passkey_hash": "", "passkey_set": False, "security": {}}

    def _save_config(self):
        """Save updated config back to config.json."""
        try:
            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"[AUTH] Error saving config: {e}")

    @staticmethod
    def hash_passkey(passkey_phrase):
        """Hash a passkey phrase using SHA-256."""
        # Normalize: lowercase, strip extra whitespace, join words
        normalized = " ".join(passkey_phrase.lower().strip().split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def is_passkey_configured(self):
        """Check if a passkey has been set up."""
        return self.config.get("passkey_set", False) and bool(self.config.get("passkey_hash", ""))

    def setup_passkey(self, passkey_phrase):
        """
        One-time passkey setup during onboarding.
        Hashes the spoken phrase and stores it in config.
        Returns True on success.
        """
        if not passkey_phrase or len(passkey_phrase.strip()) < 3:
            print("[AUTH] Passkey too short. Must be at least 3 characters.")
            return False

        hashed = self.hash_passkey(passkey_phrase)
        self.config["passkey_hash"] = hashed
        self.config["passkey_set"] = True
        self._save_config()
        print("[AUTH] Passkey configured successfully.")
        return True

    def verify_passkey(self, spoken_phrase):
        """
        Verify a spoken passkey against the stored hash.
        Returns True if matched, False otherwise.
        Handles lockout logic.
        """
        # Check if locked out
        if self.is_locked_out():
            remaining = int(self.lockout_until - time.time())
            print(f"[AUTH] System locked. Try again in {remaining} seconds.")
            return False

        if not self.is_passkey_configured():
            print("[AUTH] No passkey configured. Run onboarding first.")
            return False

        # Hash the spoken phrase and compare
        spoken_hash = self.hash_passkey(spoken_phrase)
        stored_hash = self.config.get("passkey_hash", "")

        if spoken_hash == stored_hash:
            # Success
            self.is_unlocked = True
            self.failed_attempts = 0
            self.last_activity_time = time.time()
            print("[AUTH] ✓ Passkey verified. System unlocked.")
            return True
        else:
            # Failure
            self.failed_attempts += 1
            print(f"[AUTH] ✗ Incorrect passkey. Attempt {self.failed_attempts}/{self.max_failed_attempts}")

            # Log failed attempt
            if self.log_failed:
                self._log_failed_attempt(spoken_phrase)

            # Check lockout
            if self.failed_attempts >= self.max_failed_attempts:
                self.lockout_until = time.time() + self.lockout_duration
                print(f"[AUTH] ⚠ Too many failed attempts. Locked for {self.lockout_duration} seconds.")

            return False

    def is_locked_out(self):
        """Check if the system is in lockout state."""
        if self.lockout_until > 0 and time.time() < self.lockout_until:
            return True
        elif self.lockout_until > 0 and time.time() >= self.lockout_until:
            # Lockout expired
            self.lockout_until = 0
            self.failed_attempts = 0
            print("[AUTH] Lockout period expired.")
            return False
        return False

    def check_idle_timeout(self):
        """Check if the system should auto-lock due to inactivity."""
        if self.is_unlocked and (time.time() - self.last_activity_time) > self.idle_timeout:
            self.lock()
            print("[AUTH] System auto-locked due to inactivity.")
            return True
        return False

    def refresh_activity(self):
        """Reset the idle timer (called on each successful interaction)."""
        self.last_activity_time = time.time()

    def lock(self):
        """Manually lock the system."""
        self.is_unlocked = False
        self.failed_attempts = 0
        print("[AUTH] System locked.")

    def unlock_bypass(self):
        """Bypass authentication (for development/testing only)."""
        self.is_unlocked = True
        self.last_activity_time = time.time()
        print("[AUTH] ⚠ System unlocked (bypass mode — development only).")

    def change_passkey(self, old_phrase, new_phrase):
        """Change the passkey by verifying the old one first."""
        old_hash = self.hash_passkey(old_phrase)
        if old_hash != self.config.get("passkey_hash", ""):
            print("[AUTH] Old passkey incorrect. Cannot change.")
            return False
        return self.setup_passkey(new_phrase)

    def _log_failed_attempt(self, spoken_phrase):
        """Log a failed authentication attempt with timestamp."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "attempt_number": self.failed_attempts,
            "phrase_length": len(spoken_phrase) if spoken_phrase else 0
        }

        try:
            if os.path.exists(self.attempt_log_path):
                with open(self.attempt_log_path, "r") as f:
                    log = json.load(f)
            else:
                log = {"failed_attempts": []}

            log["failed_attempts"].append(log_entry)

            os.makedirs(os.path.dirname(self.attempt_log_path), exist_ok=True)
            with open(self.attempt_log_path, "w") as f:
                json.dump(log, f, indent=4)

        except Exception as e:
            print(f"[AUTH] Failed to write auth log: {e}")

    def get_status(self):
        """Return current auth status dict for HUD display."""
        return {
            "unlocked": self.is_unlocked,
            "locked_out": self.is_locked_out(),
            "failed_attempts": self.failed_attempts,
            "lockout_remaining": max(0, int(self.lockout_until - time.time())) if self.lockout_until > 0 else 0,
            "idle_remaining": max(0, int(self.idle_timeout - (time.time() - self.last_activity_time)))
        }


# Convenience singleton
_instance = None

def get_auth(config_path="config.json"):
    """Get or create a singleton Authenticator instance."""
    global _instance
    if _instance is None:
        _instance = Authenticator(config_path)
    return _instance
