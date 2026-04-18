"""
NEXUS NLU Module — Natural Language Understanding & Intent Routing
Classifies user utterances into 5 intent categories using keyword scoring + regex.
Supports confidence thresholds with clarification fallback.
"""

import re
import json
import os


class NLU:
    """Natural Language Understanding engine with keyword-based intent classification."""

    # Intent categories
    INTENT_SYSTEM = "system_execution"
    INTENT_BROWSER = "browser_control"
    INTENT_QA = "question_answering"
    INTENT_SIMULATION = "simulation_decision"
    INTENT_CONFIG = "system_config"
    INTENT_UNKNOWN = "unknown"

    def __init__(self, config_path="config.json"):
        self.config = self._load_config(config_path)
        nlu_config = self.config.get("nlu", {})
        self.confidence_threshold = nlu_config.get("confidence_threshold", 0.70)
        self.use_llm = nlu_config.get("use_llm", False)

        self.intent_patterns = {
            self.INTENT_SYSTEM: {
                "keywords": [
                    "open", "launch", "start", "close", "exit", "quit",
                    "volume", "brightness", "screenshot", "lock", "shutdown",
                    "restart", "reboot", "mute", "unmute", "maximize", "minimize",
                    "file", "folder", "create", "delete", "rename", "move", "copy",
                    "terminal", "command prompt", "powershell", "notepad", "calculator",
                    "spotify", "vlc", "vscode", "code"
                ],
                "patterns": [
                    r"open\s+\w+",
                    r"launch\s+\w+",
                    r"close\s+\w+",
                    r"(turn|set)\s+(up|down)\s+(the\s+)?(volume|brightness)",
                    r"take\s+a?\s*screenshot",
                    r"lock\s+(the\s+)?(screen|computer|system)",
                    r"shut\s*down",
                    r"restart\s+(the\s+)?(computer|system)",
                    r"(create|make|new)\s+(a\s+)?(file|folder|directory)",
                    r"delete\s+(the\s+)?\w+",
                    r"run\s+(a\s+)?command",
                ],
                "weight": 1.0
            },
            self.INTENT_BROWSER: {
                "keywords": [
                    "browser", "chrome", "firefox", "edge", "safari",
                    "website", "url", "search", "google", "youtube",
                    "browse", "navigate", "go to", "type", "click",
                    "scroll", "tab", "bookmark", "refresh", "back", "forward",
                    "web", "internet", "page", "link",
                    # WhatsApp keywords
                    "whatsapp", "whats app", "message", "send message",
                    "send whatsapp", "text", "chat"
                ],
                "patterns": [
                    r"(open|launch)\s+(chrome|firefox|edge|safari|browser)",
                    r"go\s+to\s+\w+",
                    r"search\s+(for\s+)?",
                    r"type\s+(in\s+)?(the\s+)?",
                    r"(scroll|click)\s+",
                    r"open\s+(a\s+)?new\s+tab",
                    r"navigate\s+to\s+",
                    # WhatsApp patterns
                    r"send\s+(a\s+)?whatsapp\s+(message\s+)?to\s+\w+",
                    r"(message|text|whatsapp)\s+\w+\s+(saying|that|:)\s+.+",
                    r"send\s+(a\s+)?message\s+to\s+\w+",
                ],
                "weight": 1.0
            },
            self.INTENT_QA: {
                "keywords": [
                    "what", "who", "where", "when", "why", "how",
                    "tell", "explain", "define", "meaning", "calculate",
                    "solve", "answer", "question", "fact", "wikipedia",
                    "weather", "temperature", "time", "date", "math",
                    "capital", "president", "population", "distance"
                ],
                "patterns": [
                    r"what\s+is\s+",
                    r"who\s+(is|was)\s+",
                    r"where\s+is\s+",
                    r"how\s+(many|much|far|old|long)\s+",
                    r"(tell|explain)\s+(me\s+)?(about\s+)?",
                    r"calculate\s+",
                    r"solve\s+",
                    r"what('s| is)\s+the\s+(time|date|weather)",
                ],
                "weight": 1.0
            },
            self.INTENT_SIMULATION: {
                "keywords": [
                    "decide", "decision", "choose", "compare", "simulate",
                    "simulation", "optimize", "best", "option", "scenario",
                    "trade-off", "tradeoff", "route", "allocate", "allocation",
                    "analysis", "evaluate", "recommend", "suggestion",
                    "help me decide", "which is better", "pros and cons"
                ],
                "patterns": [
                    r"(help\s+me\s+)?decide\s+(between|on)\s+",
                    r"(compare|choose)\s+(between\s+)?",
                    r"(simulate|run)\s+(a\s+)?simulation",
                    r"which\s+(is|would be)\s+(better|best|optimal)",
                    r"(optimize|find)\s+(the\s+)?(best|optimal)",
                    r"(evaluate|analyze)\s+(the\s+)?options",
                ],
                "weight": 1.2
            },
            self.INTENT_CONFIG: {
                "keywords": [
                    "setting", "settings", "configure", "configuration",
                    "change", "update", "passkey", "wake word",
                    "voice", "speed", "rate", "volume",
                    "preferences", "customize", "reset", "clear memory"
                ],
                "patterns": [
                    r"change\s+(the\s+)?(passkey|wake\s*word|voice|settings?)",
                    r"(update|set)\s+(the\s+)?(volume|speed|rate|voice)",
                    r"(show|list)\s+(the\s+)?settings",
                    r"clear\s+(the\s+)?memory",
                    r"reset\s+(the\s+)?system",
                    r"configure\s+",
                ],
                "weight": 1.0
            }
        }

    def _load_config(self, config_path):
        """Load config from config.json."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        full_path = os.path.join(base_dir, config_path)
        try:
            with open(full_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {"nlu": {}}

    def classify(self, text):
        """
        Classify user text into an intent category.
        Returns dict with intent, confidence, entities, and original text.
        """
        if not text:
            return self._result(self.INTENT_UNKNOWN, 0.0, text, {})

        text_lower = text.lower().strip()
        scores = {}

        for intent, data in self.intent_patterns.items():
            score = self._score_intent(text_lower, data)
            scores[intent] = score

        if not scores or max(scores.values()) == 0:
            return self._result(self.INTENT_UNKNOWN, 0.0, text, {})

        best_intent = max(scores, key=scores.get)
        best_score = scores[best_intent]

        total = sum(scores.values())
        confidence = best_score / total if total > 0 else 0.0

        entities = self._extract_entities(text_lower, best_intent)

        if confidence < self.confidence_threshold:
            return self._result(
                best_intent, confidence, text, entities,
                needs_clarification=True,
                alternatives=self._get_alternatives(scores, total)
            )

        return self._result(best_intent, confidence, text, entities)

    def _score_intent(self, text, intent_data):
        """Score text against an intent's keywords and patterns."""
        score = 0.0
        weight = intent_data.get("weight", 1.0)

        keywords = intent_data.get("keywords", [])
        for keyword in keywords:
            if keyword in text:
                word_count = len(keyword.split())
                score += word_count * 1.0

        patterns = intent_data.get("patterns", [])
        for pattern in patterns:
            if re.search(pattern, text):
                score += 2.0

        return score * weight

    def _extract_entities(self, text, intent):
        """Extract relevant entities from the command text."""
        entities = {}

        if intent == self.INTENT_SYSTEM:
            # ── Open/Launch/Close app ──
            match = re.search(r"(open|launch|start|close|exit)\s+(.+?)(\s+and\s+|\s*$)", text)
            if match:
                entities["action"] = match.group(1)
                entities["application"] = match.group(2).strip()

            # ── File/Folder operations ──
            match = re.search(r"(create|delete|rename|move)\s+(a\s+)?(file|folder|directory)\s*(?:called|named)?\s*(.*)", text)
            if match:
                entities["action"] = match.group(1)
                entities["type"] = match.group(3)
                if match.group(4):
                    entities["name"] = match.group(4).strip()

            # ── Volume control ──
            if re.search(r"(volume|sound)", text):
                entities["volume"] = True
                if re.search(r"(up|increase|raise|louder|higher)", text):
                    entities["direction"] = "up"
                elif re.search(r"(down|decrease|lower|softer|quieter)", text):
                    entities["direction"] = "down"
                elif re.search(r"(mute|silent|off)", text):
                    entities["direction"] = "mute"
                elif re.search(r"(unmute|on)", text):
                    entities["direction"] = "unmute"

            # ── Mute/Unmute (without "volume" keyword) ──
            if re.search(r"\b(mute|unmute)\b", text) and "volume" not in entities:
                entities["volume"] = True
                entities["direction"] = "mute" if "unmute" not in text else "unmute"

            # ── Screenshot ──
            if re.search(r"screenshot|screen\s*shot|screen\s*capture|capture\s*screen|print\s*screen", text):
                entities["screenshot"] = True

            # ── Lock screen ──
            if re.search(r"lock\s*(the\s*)?(screen|computer|system|pc)", text):
                entities["lock"] = True

            # ── Shutdown ──
            if re.search(r"shut\s*down|power\s*off|turn\s*off\s*(the\s*)?(computer|system|pc)?", text):
                entities["shutdown"] = True

            # ── Restart/Reboot ──
            if re.search(r"restart|reboot", text):
                entities["restart"] = True

            # ── Brightness ──
            if re.search(r"brightness", text):
                entities["brightness"] = True
                if re.search(r"(up|increase|raise|higher|brighter)", text):
                    entities["direction"] = "up"
                elif re.search(r"(down|decrease|lower|dimmer|darker)", text):
                    entities["direction"] = "down"

        elif intent == self.INTENT_BROWSER:
            # ── WhatsApp entity extraction (check FIRST before generic browser) ──
            # Pattern: "send whatsapp message to Rahul saying hey bro"
            match = re.search(
                r"(?:send\s+(?:a\s+)?(?:whatsapp\s+)?(?:message\s+)?to|message|whatsapp|text)\s+"
                r"([a-zA-Z\s]+?)\s+(?:saying|that|:)\s+(.+)",
                text
            )
            if match:
                entities["whatsapp_contact"] = match.group(1).strip()
                entities["whatsapp_message"] = match.group(2).strip()
                return entities  # return early — no need for other browser entities

            # Pattern: "send whatsapp to Rahul saying hey"
            match = re.search(
                r"send\s+(?:a\s+)?whatsapp\s+(?:message\s+)?to\s+([a-zA-Z\s]+?)\s+(?:saying|that|:)\s+(.+)",
                text
            )
            if match:
                entities["whatsapp_contact"] = match.group(1).strip()
                entities["whatsapp_message"] = match.group(2).strip()
                return entities

            # Generic browser entities
            match = re.search(r"go\s+to\s+(.+)", text)
            if match:
                entities["url"] = match.group(1).strip()

            match = re.search(r"search\s+(?:for\s+)?(.+)", text)
            if match:
                entities["query"] = match.group(1).strip()

            match = re.search(r"type\s+(?:in\s+)?(?:the\s+)?(?:search\s+bar\s*:?\s*)?(.+)", text)
            if match:
                entities["text_to_type"] = match.group(1).strip()

            # ── Browser actions ──
            if re.search(r"scroll\s*(down|bottom)", text):
                entities["action"] = "scroll_down"
            elif re.search(r"scroll\s*(up|top)", text):
                entities["action"] = "scroll_up"
            elif re.search(r"\b(go\s+)?back\b", text) and "url" not in entities:
                entities["action"] = "back"
            elif re.search(r"\b(go\s+)?forward\b", text):
                entities["action"] = "forward"
            elif re.search(r"refresh|reload", text):
                entities["action"] = "refresh"
            elif re.search(r"new\s+tab", text):
                entities["action"] = "new_tab"
            elif re.search(r"close\s+tab", text):
                entities["action"] = "close_tab"

        elif intent == self.INTENT_QA:
            entities["question"] = text

            match = re.search(r"calculate\s+(.+)", text)
            if match:
                entities["expression"] = match.group(1).strip()
                entities["qa_type"] = "math"
            elif re.search(r"(time|date|day)", text):
                entities["qa_type"] = "datetime"
            elif re.search(r"weather", text):
                entities["qa_type"] = "weather"
            else:
                entities["qa_type"] = "general"

        elif intent == self.INTENT_SIMULATION:
            match = re.search(r"between\s+(.+)\s+and\s+(.+)", text)
            if match:
                entities["option_a"] = match.group(1).strip()
                entities["option_b"] = match.group(2).strip()

            match = re.search(r"(route|resource|decision)\s+(.*)", text)
            if match:
                entities["domain"] = match.group(1).strip()

        elif intent == self.INTENT_CONFIG:
            match = re.search(r"(change|update|set)\s+(?:the\s+)?(.+?)(?:\s+to\s+(.+))?$", text)
            if match:
                entities["setting"] = match.group(2).strip()
                if match.group(3):
                    entities["value"] = match.group(3).strip()

        return entities

    def _get_alternatives(self, scores, total):
        """Get alternative intents when confidence is low."""
        alternatives = []
        for intent, score in sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]:
            if score > 0:
                alternatives.append({
                    "intent": intent,
                    "confidence": round(score / total, 2) if total > 0 else 0
                })
        return alternatives

    @staticmethod
    def _result(intent, confidence, original_text, entities,
                needs_clarification=False, alternatives=None):
        """Build a standardized result dict."""
        return {
            "intent": intent,
            "confidence": round(confidence, 3),
            "original_text": original_text,
            "entities": entities,
            "needs_clarification": needs_clarification,
            "alternatives": alternatives or []
        }

    def get_clarification_prompt(self, result):
        """Generate a clarification question for ambiguous input."""
        if not result.get("alternatives"):
            return "I'm not sure what you mean. Could you rephrase that?"

        intent_names = {
            self.INTENT_SYSTEM: "run a system command",
            self.INTENT_BROWSER: "control the browser",
            self.INTENT_QA: "answer a question",
            self.INTENT_SIMULATION: "run a simulation",
            self.INTENT_CONFIG: "change a setting"
        }

        options = []
        for alt in result["alternatives"][:3]:
            name = intent_names.get(alt["intent"], alt["intent"])
            options.append(name)

        if len(options) == 1:
            return f"Did you mean you want me to {options[0]}?"
        else:
            joined = ", ".join(options[:-1]) + f", or {options[-1]}"
            return f"I'm not sure if you want me to {joined}. Could you clarify?"


# Convenience singleton
_instance = None

def get_nlu(config_path="config.json"):
    """Get or create a singleton NLU instance."""
    global _instance
    if _instance is None:
        _instance = NLU(config_path)
    return _instance