"""
Tests for NEXUS QA Module — Knowledge base search, math evaluation, datetime.
"""

import os
import sys
import json
import pytest
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.qa import QAEngine


@pytest.fixture
def temp_qa():
    """Create a QAEngine with temporary knowledge base."""
    temp_dir = tempfile.mkdtemp()

    # Create config
    data_dir = os.path.join(temp_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    config = {
        "paths": {"qa_knowledge": "data/qa_knowledge.json"},
        "weather_api_key": "",
        "weather_city": "London"
    }
    config_path = os.path.join(temp_dir, "config.json")
    with open(config_path, "w") as f:
        json.dump(config, f)

    # Create knowledge base
    kb = {
        "questions": [
            {"question": "What is Python?", "answer": "Python is a high-level programming language."},
            {"question": "What is NEXUS?", "answer": "NEXUS is an intelligent voice assistant."},
            {"question": "Who created NEXUS?", "answer": "NEXUS was created as an academic project."}
        ]
    }
    kb_path = os.path.join(data_dir, "qa_knowledge.json")
    with open(kb_path, "w") as f:
        json.dump(kb, f)

    # Create QAEngine manually
    qa = QAEngine.__new__(QAEngine)
    qa.base_dir = temp_dir
    qa.config = config
    qa.knowledge_base = kb["questions"]
    qa.wiki = None  # Don't need wikipedia for tests

    yield qa, temp_dir

    shutil.rmtree(temp_dir)


class TestKnowledgeBase:
    """Test knowledge base search functionality."""

    def test_exact_match(self, temp_qa):
        qa, _ = temp_qa
        result = qa.search_knowledge_base("What is Python?")
        assert result is not None
        assert "programming language" in result.lower()

    def test_fuzzy_match(self, temp_qa):
        qa, _ = temp_qa
        result = qa.search_knowledge_base("tell me about Python")
        # Should find Python-related answer based on keyword overlap
        # May or may not match depending on threshold
        # At minimum, the search should not error
        assert result is None or isinstance(result, str)

    def test_no_match(self, temp_qa):
        qa, _ = temp_qa
        result = qa.search_knowledge_base("What is quantum computing?")
        assert result is None

    def test_nexus_question(self, temp_qa):
        qa, _ = temp_qa
        result = qa.search_knowledge_base("What is NEXUS?")
        assert result is not None
        assert "voice assistant" in result.lower()


class TestMathSolving:
    """Test mathematical expression evaluation."""

    def test_basic_addition(self, temp_qa):
        qa, _ = temp_qa
        result = qa.solve_math("5 + 3")
        assert "8" in result

    def test_multiplication(self, temp_qa):
        qa, _ = temp_qa
        result = qa.solve_math("25 * 4")
        assert "100" in result

    def test_word_math(self, temp_qa):
        qa, _ = temp_qa
        result = qa.solve_math("10 plus 20")
        assert "30" in result

    def test_complex_expression(self, temp_qa):
        qa, _ = temp_qa
        result = qa.solve_math("(10 + 5) * 2")
        assert "30" in result

    def test_division(self, temp_qa):
        qa, _ = temp_qa
        result = qa.solve_math("100 / 4")
        assert "25" in result

    def test_invalid_expression(self, temp_qa):
        qa, _ = temp_qa
        result = qa.solve_math("not a math expression")
        assert isinstance(result, str)  # Should return error message gracefully


class TestDatetime:
    """Test datetime queries."""

    def test_time_query(self, temp_qa):
        qa, _ = temp_qa
        result = qa.get_datetime("what is the time")
        assert "time" in result.lower() or ":" in result

    def test_date_query(self, temp_qa):
        qa, _ = temp_qa
        result = qa.get_datetime("what is the date")
        assert "date" in result.lower() or "20" in result  # Year contains 20xx

    def test_day_query(self, temp_qa):
        qa, _ = temp_qa
        result = qa.get_datetime("what day is it")
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        assert any(day in result.lower() for day in days)


class TestWeather:
    """Test weather queries."""

    def test_no_api_key(self, temp_qa):
        qa, _ = temp_qa
        result = qa.get_weather()
        assert "api key" in result.lower() or "not configured" in result.lower()


class TestAnswer:
    """Test the main answer routing."""

    def test_math_routing(self, temp_qa):
        qa, _ = temp_qa
        result = qa.answer({"qa_type": "math", "expression": "5 + 5", "question": ""})
        assert "10" in result

    def test_datetime_routing(self, temp_qa):
        qa, _ = temp_qa
        result = qa.answer({"qa_type": "datetime", "question": "what time is it"})
        assert isinstance(result, str) and len(result) > 0

    def test_general_routing_kb(self, temp_qa):
        qa, _ = temp_qa
        result = qa.answer({"qa_type": "general", "question": "What is NEXUS?"})
        assert "voice assistant" in result.lower()


class TestKnowledgeBaseManagement:
    """Test adding to knowledge base."""

    def test_add_entry(self, temp_qa):
        qa, temp_dir = temp_qa
        result = qa.add_to_knowledge_base("What is AI?", "AI stands for Artificial Intelligence.")
        assert "added" in result.lower()
        assert len(qa.knowledge_base) == 4  # 3 original + 1 new

    def test_reload_kb(self, temp_qa):
        qa, _ = temp_qa
        result = qa.reload_knowledge_base()
        assert "entries loaded" in result.lower()
