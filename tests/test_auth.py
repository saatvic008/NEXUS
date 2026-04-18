"""
Tests for NEXUS Auth Module — Passkey hashing, verification, lockout logic.
"""

import os
import sys
import json
import time
import pytest
import tempfile
import shutil

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.auth import Authenticator


@pytest.fixture
def temp_config():
    """Create a temporary config for testing."""
    temp_dir = tempfile.mkdtemp()
    config = {
        "passkey_hash": "",
        "passkey_set": False,
        "security": {
            "max_failed_attempts": 3,
            "lockout_duration_seconds": 2,
            "idle_timeout_seconds": 5,
            "log_failed_attempts": True
        }
    }
    config_path = os.path.join(temp_dir, "config.json")
    with open(config_path, "w") as f:
        json.dump(config, f)

    # Create data directory for auth log
    os.makedirs(os.path.join(temp_dir, "data"), exist_ok=True)

    yield temp_dir, config_path

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def auth(temp_config):
    """Create an Authenticator with temporary config."""
    temp_dir, config_path = temp_config
    # We need to trick the auth module into using our temp directory
    a = Authenticator.__new__(Authenticator)
    a.base_dir = temp_dir
    a.config_path = config_path
    a.config = json.load(open(config_path))
    a.is_unlocked = False
    a.failed_attempts = 0
    a.lockout_until = 0
    a.last_activity_time = time.time()
    a.max_failed_attempts = 3
    a.lockout_duration = 2
    a.idle_timeout = 5
    a.log_failed = True
    a.attempt_log_path = os.path.join(temp_dir, "data", "auth_log.json")
    return a


class TestPasskeyHashing:
    """Test passkey hashing functionality."""

    def test_hash_consistency(self):
        """Same input should always produce the same hash."""
        hash1 = Authenticator.hash_passkey("nexus override alpha")
        hash2 = Authenticator.hash_passkey("nexus override alpha")
        assert hash1 == hash2

    def test_hash_normalization(self):
        """Hashing should normalize whitespace and case."""
        hash1 = Authenticator.hash_passkey("Nexus Override Alpha")
        hash2 = Authenticator.hash_passkey("nexus  override  alpha")
        hash3 = Authenticator.hash_passkey("  nexus override alpha  ")
        assert hash1 == hash2 == hash3

    def test_hash_different_inputs(self):
        """Different inputs should produce different hashes."""
        hash1 = Authenticator.hash_passkey("nexus override alpha")
        hash2 = Authenticator.hash_passkey("nexus override beta")
        assert hash1 != hash2

    def test_hash_is_sha256(self):
        """Hash should be a valid SHA-256 hex string (64 chars)."""
        h = Authenticator.hash_passkey("test passkey")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


class TestPasskeySetup:
    """Test passkey setup and configuration."""

    def test_setup_passkey(self, auth):
        """Should successfully set up a passkey."""
        result = auth.setup_passkey("nexus override alpha")
        assert result is True
        assert auth.is_passkey_configured()

    def test_setup_too_short(self, auth):
        """Should reject passkeys shorter than 3 characters."""
        result = auth.setup_passkey("ab")
        assert result is False

    def test_setup_empty(self, auth):
        """Should reject empty passkeys."""
        result = auth.setup_passkey("")
        assert result is False


class TestPasskeyVerification:
    """Test passkey verification logic."""

    def test_correct_passkey(self, auth):
        """Should unlock on correct passkey."""
        auth.setup_passkey("nexus override alpha")
        result = auth.verify_passkey("nexus override alpha")
        assert result is True
        assert auth.is_unlocked is True

    def test_incorrect_passkey(self, auth):
        """Should reject incorrect passkey."""
        auth.setup_passkey("nexus override alpha")
        result = auth.verify_passkey("wrong phrase")
        assert result is False
        assert auth.is_unlocked is False

    def test_failed_attempts_counter(self, auth):
        """Should track failed attempts."""
        auth.setup_passkey("nexus override alpha")
        auth.verify_passkey("wrong1")
        assert auth.failed_attempts == 1
        auth.verify_passkey("wrong2")
        assert auth.failed_attempts == 2

    def test_reset_on_success(self, auth):
        """Should reset failed attempts on success."""
        auth.setup_passkey("nexus override alpha")
        auth.verify_passkey("wrong")
        auth.verify_passkey("nexus override alpha")
        assert auth.failed_attempts == 0


class TestLockout:
    """Test lockout logic."""

    def test_lockout_after_max_attempts(self, auth):
        """Should lock out after max failed attempts."""
        auth.setup_passkey("nexus override alpha")
        for _ in range(3):
            auth.verify_passkey("wrong")
        assert auth.is_locked_out() is True

    def test_lockout_prevents_verification(self, auth):
        """Should reject verification during lockout."""
        auth.setup_passkey("nexus override alpha")
        for _ in range(3):
            auth.verify_passkey("wrong")
        result = auth.verify_passkey("nexus override alpha")
        assert result is False

    def test_lockout_expires(self, auth):
        """Should expire lockout after cooldown period."""
        auth.setup_passkey("nexus override alpha")
        for _ in range(3):
            auth.verify_passkey("wrong")
        assert auth.is_locked_out() is True
        time.sleep(2.5)  # Wait for lockout to expire
        assert auth.is_locked_out() is False


class TestIdleTimeout:
    """Test idle timeout logic."""

    def test_idle_timeout(self, auth):
        """Should auto-lock after idle timeout."""
        auth.setup_passkey("test")
        auth.verify_passkey("test")
        assert auth.is_unlocked is True
        auth.last_activity_time = time.time() - 10  # Simulate 10 seconds idle
        assert auth.check_idle_timeout() is True
        assert auth.is_unlocked is False

    def test_activity_refresh(self, auth):
        """Should reset idle timer on activity."""
        auth.setup_passkey("test")
        auth.verify_passkey("test")
        auth.refresh_activity()
        assert auth.check_idle_timeout() is False


class TestLockUnlock:
    """Test manual lock/unlock."""

    def test_manual_lock(self, auth):
        """Should manually lock the system."""
        auth.is_unlocked = True
        auth.lock()
        assert auth.is_unlocked is False

    def test_unlock_bypass(self, auth):
        """Should bypass authentication in dev mode."""
        auth.unlock_bypass()
        assert auth.is_unlocked is True

    def test_change_passkey(self, auth):
        """Should change passkey with correct old key."""
        auth.setup_passkey("old passkey")
        result = auth.change_passkey("old passkey", "new passkey")
        assert result is True
        assert auth.verify_passkey("new passkey") is True

    def test_change_passkey_wrong_old(self, auth):
        """Should reject passkey change with wrong old key."""
        auth.setup_passkey("old passkey")
        result = auth.change_passkey("wrong old", "new passkey")
        assert result is False
