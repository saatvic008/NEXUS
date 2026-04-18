"""
NEXUS QA Module — Question Answering & Academic Intelligence
Handles instructor Q&A from knowledge base, math calculations, Wikipedia, time/date/weather.
"""

import json
import os
import re
import math
from datetime import datetime

try:
    import sympy
    SYMPY_AVAILABLE = True
except ImportError:
    SYMPY_AVAILABLE = False

try:
    import wikipediaapi
    WIKIPEDIA_AVAILABLE = True
except ImportError:
    WIKIPEDIA_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class QAEngine:
    """Question answering engine with local KB, math, Wikipedia, and weather support."""

    def __init__(self, config_path="config.json"):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config = self._load_config(config_path)
        self.knowledge_base = self._load_knowledge_base()

        # Wikipedia API
        if WIKIPEDIA_AVAILABLE:
            self.wiki = wikipediaapi.Wikipedia(
                user_agent="NEXUS/1.0 (Intelligent Voice Assistant)",
                language="en"
            )
        else:
            self.wiki = None

    def _load_config(self, config_path):
        """Load config from config.json."""
        full_path = os.path.join(self.base_dir, config_path)
        try:
            with open(full_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def _load_knowledge_base(self):
        """Load instructor Q&A knowledge base from JSON file."""
        kb_path = self.config.get("paths", {}).get("qa_knowledge", "data/qa_knowledge.json")
        full_path = os.path.join(self.base_dir, kb_path)
        try:
            with open(full_path, "r") as f:
                data = json.load(f)
            return data.get("questions", [])
        except FileNotFoundError:
            print("[QA] Knowledge base not found. Starting with empty KB.")
            return []

    def answer(self, entities):
        """
        Route question to appropriate handler based on qa_type.
        Returns the answer string.
        """
        qa_type = entities.get("qa_type", "general")
        question = entities.get("question", "")

        if qa_type == "math":
            expression = entities.get("expression", question)
            return self.solve_math(expression)
        elif qa_type == "datetime":
            return self.get_datetime(question)
        elif qa_type == "weather":
            return self.get_weather()
        else:
            # Try knowledge base first, then Wikipedia
            kb_answer = self.search_knowledge_base(question)
            if kb_answer:
                return kb_answer
            return self.search_wikipedia(question)

    def search_knowledge_base(self, question):
        """
        Search the local instructor Q&A knowledge base.
        Uses fuzzy keyword matching against stored questions.
        """
        if not self.knowledge_base:
            return None

        question_lower = question.lower().strip()
        question_words = set(re.findall(r'\w+', question_lower))

        best_match = None
        best_score = 0

        for entry in self.knowledge_base:
            stored_q = entry.get("question", "").lower()
            stored_words = set(re.findall(r'\w+', stored_q))

            # Calculate word overlap score
            if stored_words:
                common = question_words & stored_words
                score = len(common) / max(len(stored_words), len(question_words))

                if score > best_score and score > 0.65:  # 65% threshold
                    best_score = score
                    best_match = entry

        if best_match:
            return best_match.get("answer", "I found a match but no answer is stored.")

        return None

    def solve_math(self, expression):
        """Solve a mathematical expression using sympy or eval."""
        # Clean up the expression
        expression = expression.strip()
        expression = expression.replace("plus", "+").replace("minus", "-")
        expression = expression.replace("times", "*").replace("multiplied by", "*")
        expression = expression.replace("divided by", "/").replace("over", "/")
        expression = expression.replace("to the power of", "**").replace("power", "**")
        expression = expression.replace("squared", "**2").replace("cubed", "**3")
        expression = expression.replace("square root of", "sqrt")

        try:
            if SYMPY_AVAILABLE:
                # Use sympy for safe evaluation
                result = sympy.sympify(expression)
                # Try to get a numerical value
                try:
                    numerical = float(result.evalf())
                    if numerical == int(numerical):
                        return f"The answer is {int(numerical)}."
                    return f"The answer is {round(numerical, 6)}."
                except (TypeError, ValueError):
                    return f"The result is {result}."
            else:
                # Fallback: restricted eval with math module
                allowed_names = {
                    "abs": abs, "round": round, "min": min, "max": max,
                    "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos,
                    "tan": math.tan, "pi": math.pi, "e": math.e,
                    "log": math.log, "log10": math.log10, "pow": pow,
                }
                # Only allow safe characters
                safe_expr = re.sub(r'[^0-9+\-*/.()%\s]', '', expression)
                if safe_expr:
                    result = eval(safe_expr, {"__builtins__": {}}, allowed_names)
                    return f"The answer is {result}."
                else:
                    return "I couldn't parse that math expression."

        except Exception as e:
            return f"I couldn't solve that: {e}"

    def get_datetime(self, question=""):
        """Return current date, time, or day."""
        now = datetime.now()
        question_lower = question.lower()

        if "date" in question_lower:
            return f"Today's date is {now.strftime('%A, %B %d, %Y')}."
        elif "day" in question_lower:
            return f"Today is {now.strftime('%A')}."
        elif "time" in question_lower:
            return f"The current time is {now.strftime('%I:%M %p')}."
        else:
            return f"It is {now.strftime('%I:%M %p')} on {now.strftime('%A, %B %d, %Y')}."

    def get_weather(self, city=None):
        """Get current weather using a weather API."""
        if not REQUESTS_AVAILABLE:
            return "Cannot fetch weather — requests library not installed."

        api_key = self.config.get("weather_api_key", "")
        if not api_key:
            return "Weather API key not configured. Please add your API key to config.json."

        city = city or self.config.get("weather_city", "New York")

        try:
            url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
            response = requests.get(url, timeout=10)
            data = response.json()

            if response.status_code == 200:
                temp = data["main"]["temp"]
                desc = data["weather"][0]["description"]
                humidity = data["main"]["humidity"]
                return f"The weather in {city} is {desc} with a temperature of {temp}°C and humidity at {humidity}%."
            else:
                return f"Couldn't fetch weather data: {data.get('message', 'API error')}."

        except Exception as e:
            return f"Weather request failed: {e}"

    def search_wikipedia(self, question):
        """Search Wikipedia for an answer."""
        if not self.wiki:
            return self._fallback_answer(question)

        # Extract search topic from question
        topic = self._extract_topic(question)
        if not topic:
            return "I'm not sure what to look up. Could you rephrase that?"

        try:
            page = self.wiki.page(topic)
            if page.exists():
                # Return first 2 sentences of the summary
                summary = page.summary
                sentences = summary.split('. ')
                short_answer = '. '.join(sentences[:2]) + '.'
                return short_answer
            else:
                return f"I couldn't find information about '{topic}'. Try rephrasing your question."

        except Exception as e:
            return f"Wikipedia search failed: {e}"

    def _extract_topic(self, question):
        """Extract the main topic from a question."""
        question = question.lower().strip()

        # Remove common question starters
        starters = [
            r"what is (a |an |the )?",
            r"who is (a |an |the )?",
            r"where is (a |an |the )?",
            r"tell me about (a |an |the )?",
            r"explain (a |an |the )?",
            r"define (a |an |the )?",
            r"what are (a |an |the )?",
        ]

        for pattern in starters:
            match = re.match(pattern, question)
            if match:
                topic = question[match.end():].strip().rstrip("?. ")
                return topic

        # Fallback: use the whole question
        return question.rstrip("?. ")

    def _fallback_answer(self, question):
        """Provide a fallback answer when no API is available."""
        return (
            "I don't have enough information to answer that question right now. "
            "You can add answers to the knowledge base in data/qa_knowledge.json, "
            "or install the wikipedia-api package for online lookups."
        )

    def add_to_knowledge_base(self, question, answer):
        """Add a new Q&A pair to the knowledge base."""
        new_entry = {"question": question, "answer": answer}
        self.knowledge_base.append(new_entry)

        # Save to file
        kb_path = self.config.get("paths", {}).get("qa_knowledge", "data/qa_knowledge.json")
        full_path = os.path.join(self.base_dir, kb_path)
        try:
            with open(full_path, "w") as f:
                json.dump({"questions": self.knowledge_base}, f, indent=4)
            return f"Added to knowledge base: '{question}'"
        except Exception as e:
            return f"Failed to save to knowledge base: {e}"

    def reload_knowledge_base(self):
        """Reload the knowledge base from disk."""
        self.knowledge_base = self._load_knowledge_base()
        return f"Knowledge base reloaded. {len(self.knowledge_base)} entries loaded."


# Convenience singleton
_instance = None

def get_qa(config_path="config.json"):
    """Get or create a singleton QAEngine instance."""
    global _instance
    if _instance is None:
        _instance = QAEngine(config_path)
    return _instance
