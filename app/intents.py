"""
Lightweight rule-based intent detector.

This is intentionally simple (regex/keyword matching, no ML model) so
the project keeps working with zero extra dependencies and in fully
offline/local-fallback mode. It routes each user message to a handler
in chatbot.py.
"""

import re
from enum import Enum


class Intent(str, Enum):
    GREETING = "greeting"
    FAREWELL = "farewell"
    CALCULATION = "calculation"
    DATETIME = "datetime"
    FILE_QUESTION = "file_question"
    SMALLTALK = "smalltalk"
    GENERAL = "general"


_GREETING_WORDS = {"hello", "hi", "hey", "namaste", "yo"}
_FAREWELL_WORDS = {"bye", "goodbye", "exit", "quit", "see you"}
_DATETIME_WORDS = {"date", "time", "day", "today", "year", "month"}
_FILE_WORDS = {
    "document", "file", "pdf", "uploaded", "attachment", "in the doc",
    "in the file", "according to the document",
}

# Matches things like "2 + 2", "calculate 5*3", "what is 10 / 2"
_CALC_PATTERN = re.compile(
    r"(?:calculate|compute|what\s+is)?\s*"
    r"(-?\d+(?:\.\d+)?\s*[\+\-\*/%]\s*-?\d+(?:\.\d+)?"
    r"(?:\s*[\+\-\*/%]\s*-?\d+(?:\.\d+)?)*)",
)


class IntentDetector:
    def detect(self, text: str) -> Intent:
        lowered = text.lower().strip()

        if any(word in lowered for word in _FAREWELL_WORDS):
            return Intent.FAREWELL

        if self.extract_expression(lowered):
            return Intent.CALCULATION

        if any(word in lowered for word in _DATETIME_WORDS):
            return Intent.DATETIME

        if any(word in lowered for word in _FILE_WORDS):
            return Intent.FILE_QUESTION

        if any(word == lowered.strip("!?. ") or lowered.startswith(word)
               for word in _GREETING_WORDS):
            return Intent.GREETING

        return Intent.GENERAL

    @staticmethod
    def extract_expression(text: str):
        match = _CALC_PATTERN.search(text)
        if match:
            return match.group(1).strip()
        return None
