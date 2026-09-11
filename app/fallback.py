"""
Local, no-API fallback responder.

This preserves the behaviour of the ORIGINAL nexa.py: a simple
dictionary of keyword -> canned response, used whenever no LLM
provider/key is configured, or when the LLM call fails for any reason.
It guarantees NEXA always answers something, even fully offline.
"""

from typing import Optional

# Original responses from nexa.py, kept as-is, plus a few natural
# additions so the fallback feels a bit more complete.
FALLBACK_RESPONSES = {
    "how are you": "I am very fine. Thank you!",
    "who are you": "I am NEXA, an AI chatbot.",
    "what is your name": "My name is NEXA.",
    "motivate me": "Keep going. Every bug in your project makes you a better developer.",
    "happy": "Great to hear that!",
    "thank you": "You're welcome!",
    "thanks": "You're welcome!",
    "help": "You can ask me questions, do quick maths, ask the date/time, "
            "or upload a document and ask me about it.",
}

DEFAULT_FALLBACK = (
    "I am not able to tell that yet. Main jald hi yeh sikh lunga!"
)


def get_greeting_reply(user_name: str) -> str:
    return f"Hi {user_name}, welcome! How can I help you?"


def get_fallback_reply(user_input: str) -> str:
    lowered = user_input.lower()
    for key, reply in FALLBACK_RESPONSES.items():
        if key in lowered:
            return reply
    return DEFAULT_FALLBACK


def time_based_greeting(user_name: str, hour: Optional[int] = None) -> str:
    """Original time-of-day greeting logic from nexa.py, preserved."""
    import datetime

    if hour is None:
        hour = datetime.datetime.now().hour

    if 5 <= hour <= 11:
        return f"Good Morning {user_name}"
    if 11 <= hour <= 17:
        return f"Good Afternoon {user_name}"
    if 17 <= hour <= 20:
        return f"Good Evening {user_name}"
    return f"Good Night {user_name}"
