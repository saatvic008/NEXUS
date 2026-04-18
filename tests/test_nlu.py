"""
Tests for NEXUS NLU Module — Intent classification across all five categories.
"""

import os
import sys
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.nlu import NLU


@pytest.fixture
def nlu():
    """Create an NLU instance for testing."""
    # Use a non-existent config path so it falls back to defaults
    n = NLU.__new__(NLU)
    n.config = {"nlu": {"confidence_threshold": 0.70}}
    n.confidence_threshold = 0.70
    n.use_llm = False
    n.intent_patterns = NLU().__dict__["intent_patterns"]
    return n


class TestSystemIntent:
    """Test system execution intent classification."""

    def test_open_application(self, nlu):
        result = nlu.classify("open notepad")
        assert result["intent"] == NLU.INTENT_SYSTEM

    def test_launch_application(self, nlu):
        result = nlu.classify("launch spotify")
        assert result["intent"] == NLU.INTENT_SYSTEM

    def test_close_application(self, nlu):
        result = nlu.classify("close calculator")
        assert result["intent"] == NLU.INTENT_SYSTEM

    def test_take_screenshot(self, nlu):
        result = nlu.classify("take a screenshot")
        assert result["intent"] == NLU.INTENT_SYSTEM

    def test_volume_control(self, nlu):
        result = nlu.classify("turn up the volume")
        assert result["intent"] == NLU.INTENT_SYSTEM

    def test_lock_screen(self, nlu):
        result = nlu.classify("lock the screen")
        assert result["intent"] == NLU.INTENT_SYSTEM

    def test_shutdown(self, nlu):
        result = nlu.classify("shut down the computer")
        assert result["intent"] == NLU.INTENT_SYSTEM

    def test_create_folder(self, nlu):
        result = nlu.classify("create a folder called projects")
        assert result["intent"] == NLU.INTENT_SYSTEM


class TestBrowserIntent:
    """Test browser control intent classification."""

    def test_open_chrome(self, nlu):
        result = nlu.classify("open chrome")
        # Could be system or browser — both are valid since "chrome" is in both
        assert result["intent"] in [NLU.INTENT_SYSTEM, NLU.INTENT_BROWSER]

    def test_go_to_url(self, nlu):
        result = nlu.classify("go to youtube.com")
        assert result["intent"] == NLU.INTENT_BROWSER

    def test_search_google(self, nlu):
        result = nlu.classify("search for python tutorials")
        assert result["intent"] == NLU.INTENT_BROWSER

    def test_type_in_search(self, nlu):
        result = nlu.classify("type in the search bar best python projects")
        assert result["intent"] == NLU.INTENT_BROWSER

    def test_scroll_down(self, nlu):
        result = nlu.classify("scroll down the page")
        assert result["intent"] == NLU.INTENT_BROWSER

    def test_navigate_url(self, nlu):
        result = nlu.classify("navigate to google.com")
        assert result["intent"] == NLU.INTENT_BROWSER


class TestQAIntent:
    """Test question answering intent classification."""

    def test_what_is_question(self, nlu):
        result = nlu.classify("what is artificial intelligence")
        assert result["intent"] == NLU.INTENT_QA

    def test_who_is_question(self, nlu):
        result = nlu.classify("who is Albert Einstein")
        assert result["intent"] == NLU.INTENT_QA

    def test_calculate(self, nlu):
        result = nlu.classify("calculate 25 times 47")
        assert result["intent"] == NLU.INTENT_QA

    def test_time_query(self, nlu):
        result = nlu.classify("what is the time")
        assert result["intent"] == NLU.INTENT_QA

    def test_weather_query(self, nlu):
        result = nlu.classify("what is the weather today")
        assert result["intent"] == NLU.INTENT_QA

    def test_explain_question(self, nlu):
        result = nlu.classify("explain machine learning")
        assert result["intent"] == NLU.INTENT_QA


class TestSimulationIntent:
    """Test simulation decision intent classification."""

    def test_decide_between(self, nlu):
        result = nlu.classify("help me decide between route A and route B")
        assert result["intent"] == NLU.INTENT_SIMULATION

    def test_compare_options(self, nlu):
        result = nlu.classify("compare option A and option B")
        assert result["intent"] == NLU.INTENT_SIMULATION

    def test_run_simulation(self, nlu):
        result = nlu.classify("simulate a decision scenario")
        assert result["intent"] == NLU.INTENT_SIMULATION

    def test_optimize_query(self, nlu):
        result = nlu.classify("find the optimal route for my commute")
        assert result["intent"] == NLU.INTENT_SIMULATION

    def test_which_is_better(self, nlu):
        result = nlu.classify("which is better plan A or plan B")
        assert result["intent"] == NLU.INTENT_SIMULATION


class TestConfigIntent:
    """Test system configuration intent classification."""

    def test_change_passkey(self, nlu):
        result = nlu.classify("change the passkey")
        assert result["intent"] == NLU.INTENT_CONFIG

    def test_update_voice(self, nlu):
        result = nlu.classify("update the voice settings")
        assert result["intent"] == NLU.INTENT_CONFIG

    def test_show_settings(self, nlu):
        result = nlu.classify("show the settings")
        assert result["intent"] == NLU.INTENT_CONFIG

    def test_clear_memory(self, nlu):
        result = nlu.classify("clear the memory")
        assert result["intent"] == NLU.INTENT_CONFIG


class TestEntityExtraction:
    """Test entity extraction from commands."""

    def test_app_name_extraction(self, nlu):
        result = nlu.classify("open spotify")
        assert result["entities"].get("application") == "spotify"

    def test_url_extraction(self, nlu):
        result = nlu.classify("go to youtube.com")
        assert "youtube" in result["entities"].get("url", "").lower()

    def test_search_query_extraction(self, nlu):
        result = nlu.classify("search for python tutorials")
        assert "python tutorials" in result["entities"].get("query", "")

    def test_math_expression(self, nlu):
        result = nlu.classify("calculate 5 plus 3")
        assert result["entities"].get("qa_type") == "math"

    def test_simulation_options(self, nlu):
        result = nlu.classify("decide between plan A and plan B")
        entities = result["entities"]
        assert "plan a" in entities.get("option_a", "").lower() or "plan" in str(entities).lower()


class TestConfidence:
    """Test confidence scoring."""

    def test_high_confidence(self, nlu):
        result = nlu.classify("open notepad")
        assert result["confidence"] > 0

    def test_empty_input(self, nlu):
        result = nlu.classify("")
        assert result["intent"] == NLU.INTENT_UNKNOWN

    def test_none_input(self, nlu):
        result = nlu.classify(None)
        assert result["intent"] == NLU.INTENT_UNKNOWN

    def test_result_structure(self, nlu):
        result = nlu.classify("open notepad")
        assert "intent" in result
        assert "confidence" in result
        assert "entities" in result
        assert "original_text" in result
        assert "needs_clarification" in result


class TestClarification:
    """Test clarification prompt generation."""

    def test_clarification_prompt(self, nlu):
        # Create a result that needs clarification
        result = {
            "needs_clarification": True,
            "alternatives": [
                {"intent": NLU.INTENT_SYSTEM, "confidence": 0.4},
                {"intent": NLU.INTENT_BROWSER, "confidence": 0.35}
            ]
        }
        prompt = nlu.get_clarification_prompt(result)
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_no_alternatives_prompt(self, nlu):
        result = {"alternatives": []}
        prompt = nlu.get_clarification_prompt(result)
        assert "rephrase" in prompt.lower()
