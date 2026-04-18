"""
Tests for NEXUS Decision Engine — Simulation scoring, domain loading, RL memory boost.
"""

import os
import sys
import json
import pytest
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Check for numpy
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

from core.decision_engine import DecisionEngine


@pytest.fixture
def temp_engine():
    """Create a DecisionEngine with temporary data."""
    temp_dir = tempfile.mkdtemp()

    # Create config
    data_dir = os.path.join(temp_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    config = {
        "paths": {"decision_history": "data/decision_history.json"}
    }
    config_path = os.path.join(temp_dir, "config.json")
    with open(config_path, "w") as f:
        json.dump(config, f)

    # Create empty decision history
    history = {"decisions": [], "domain_weights": {}}
    history_path = os.path.join(data_dir, "decision_history.json")
    with open(history_path, "w") as f:
        json.dump(history, f)

    # Create engine manually
    engine = DecisionEngine.__new__(DecisionEngine)
    engine.base_dir = temp_dir
    engine.config = config
    engine.decision_history = history
    engine.domains = {}
    engine.DEFAULT_N_SIMULATIONS = 100  # Fewer for faster tests
    engine.MEMORY_BOOST_FACTOR = 0.15

    yield engine, temp_dir

    shutil.rmtree(temp_dir)


@pytest.mark.skipif(not NUMPY_AVAILABLE, reason="NumPy not installed")
class TestGeneralDecision:
    """Test general decision analysis."""

    def test_basic_decision(self, temp_engine):
        engine, _ = temp_engine
        entities = {
            "option_a": "Plan A",
            "option_b": "Plan B",
            "domain": "general"
        }
        result = engine.decide(entities)
        assert result["success"] is True
        assert result["winner"] in ["Plan A", "Plan B"]
        assert "results" in result
        assert "spoken" in result

    def test_result_structure(self, temp_engine):
        engine, _ = temp_engine
        entities = {
            "option_a": "Alpha",
            "option_b": "Beta",
            "domain": "general"
        }
        result = engine.decide(entities)
        winner_data = result["results"][result["winner"]]
        assert "mean" in winner_data
        assert "std" in winner_data
        assert "median" in winner_data
        assert "best_case" in winner_data
        assert "worst_case" in winner_data

    def test_scores_in_range(self, temp_engine):
        engine, _ = temp_engine
        entities = {
            "option_a": "X",
            "option_b": "Y"
        }
        result = engine.decide(entities)
        for option, data in result["results"].items():
            assert 0.0 <= data["mean"] <= 2.0  # Can be >1 with boost
            assert data["best_case"] >= data["worst_case"]

    def test_multiple_options(self, temp_engine):
        engine, _ = temp_engine
        entities = {
            "options": ["Option 1", "Option 2", "Option 3"],
            "option_a": "Option 1",
            "option_b": "Option 2"
        }
        result = engine.decide(entities)
        assert result["success"] is True


@pytest.mark.skipif(not NUMPY_AVAILABLE, reason="NumPy not installed")
class TestMemoryBoost:
    """Test RL-inspired memory boost."""

    def test_no_history_no_boost(self, temp_engine):
        engine, _ = temp_engine
        boost = engine._get_memory_boost("New Option")
        assert boost == 0.0

    def test_boost_with_history(self, temp_engine):
        engine, _ = temp_engine
        # Add some history favoring "Plan A"
        engine.decision_history["decisions"] = [
            {"winner": "Plan A", "timestamp": "2024-01-01"},
            {"winner": "Plan A", "timestamp": "2024-01-02"},
            {"winner": "Plan B", "timestamp": "2024-01-03"},
        ]
        boost_a = engine._get_memory_boost("Plan A")
        boost_b = engine._get_memory_boost("Plan B")
        assert boost_a > boost_b

    def test_boost_factor_limit(self, temp_engine):
        engine, _ = temp_engine
        engine.decision_history["decisions"] = [
            {"winner": "Always Win", "timestamp": f"2024-01-{i:02d}"}
            for i in range(1, 11)
        ]
        boost = engine._get_memory_boost("Always Win")
        assert boost <= engine.MEMORY_BOOST_FACTOR


@pytest.mark.skipif(not NUMPY_AVAILABLE, reason="NumPy not installed")
class TestDecisionHistory:
    """Test decision history recording."""

    def test_record_decision(self, temp_engine):
        engine, _ = temp_engine
        entities = {"option_a": "A", "option_b": "B"}
        engine.decide(entities)
        assert len(engine.decision_history["decisions"]) >= 1

    def test_history_summary(self, temp_engine):
        engine, _ = temp_engine
        # Empty history
        summary = engine.get_history_summary()
        assert "no decisions" in summary.lower()

        # After a decision
        entities = {"option_a": "X", "option_b": "Y"}
        engine.decide(entities)
        summary = engine.get_history_summary()
        assert "1" in summary


class TestExplanation:
    """Test explanation generation."""

    @pytest.mark.skipif(not NUMPY_AVAILABLE, reason="NumPy not installed")
    def test_explanation_is_spoken(self, temp_engine):
        engine, _ = temp_engine
        entities = {"option_a": "Fast Route", "option_b": "Scenic Route"}
        result = engine.decide(entities)
        spoken = result.get("spoken", "")
        assert len(spoken) > 0
        assert result["winner"] in spoken

    @pytest.mark.skipif(not NUMPY_AVAILABLE, reason="NumPy not installed")
    def test_explanation_format(self, temp_engine):
        engine, _ = temp_engine
        entities = {"option_a": "A", "option_b": "B"}
        result = engine.decide(entities)
        spoken = result["spoken"]
        assert "recommend" in spoken.lower() or "simulations" in spoken.lower()


class TestNoNumpy:
    """Test behavior when NumPy is not available."""

    def test_no_numpy_fallback(self, temp_engine):
        engine, _ = temp_engine
        # Temporarily pretend numpy isn't available
        import core.decision_engine as de
        original = de.NUMPY_AVAILABLE
        de.NUMPY_AVAILABLE = False
        try:
            result = engine.decide({"option_a": "A", "option_b": "B"})
            # Should gracefully handle missing numpy
        finally:
            de.NUMPY_AVAILABLE = original
