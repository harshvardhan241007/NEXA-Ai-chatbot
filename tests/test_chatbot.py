import os
import tempfile
import pytest

from app.chatbot import NexaChatbot
from app.fallback import get_fallback_reply, time_based_greeting


@pytest.fixture
def bot():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    b = NexaChatbot(db_path=path)
    yield b
    if os.path.exists(path):
        os.remove(path)


def test_fallback_dictionary_preserved():
    assert "fine" in get_fallback_reply("how are you").lower()
    assert "nexa" in get_fallback_reply("who are you").lower()


def test_fallback_default_message():
    reply = get_fallback_reply("something totally unknown xyz")
    assert "not able to tell" in reply.lower()


def test_time_based_greeting_morning():
    assert "morning" in time_based_greeting("Sam", hour=8).lower()


def test_time_based_greeting_night():
    assert "night" in time_based_greeting("Sam", hour=2).lower()


def test_chatbot_calculation_end_to_end(bot):
    session_id = bot.start_session("Sam")
    reply = bot.handle_message(session_id, "Sam", "what is 6 * 7")
    assert "42" in reply


def test_chatbot_farewell_end_to_end(bot):
    session_id = bot.start_session("Sam")
    reply = bot.handle_message(session_id, "Sam", "bye")
    assert "bye" in reply.lower()


def test_chatbot_general_uses_local_fallback_without_api_key(bot):
    session_id = bot.start_session("Sam")
    reply = bot.handle_message(session_id, "Sam", "motivate me")
    assert "developer" in reply.lower()


def test_chatbot_document_qa(bot):
    session_id = bot.start_session("Sam")
    bot.load_document(session_id, "NEXA supports a calculator and date/time tool.")
    reply = bot.handle_message(session_id, "Sam", "what does the document say about the calculator")
    assert "calculator" in reply.lower()
