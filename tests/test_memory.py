import os
import tempfile
import pytest

from app.memory import ConversationMemory


@pytest.fixture
def memory():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)  # let init_db create a fresh file
    mem = ConversationMemory(db_path=path)
    yield mem
    if os.path.exists(path):
        os.remove(path)


def test_create_session_returns_id(memory):
    session_id = memory.create_session("Alice")
    assert session_id


def test_add_and_get_history(memory):
    session_id = memory.create_session("Bob")
    memory.add_message(session_id, "user", "hello")
    memory.add_message(session_id, "bot", "hi Bob")

    history = memory.get_history(session_id)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "hello"
    assert history[1]["role"] == "bot"


def test_get_context_string_formats_speakers(memory):
    session_id = memory.create_session("Carol")
    memory.add_message(session_id, "user", "hi")
    memory.add_message(session_id, "bot", "hello!")

    ctx = memory.get_context_string(session_id)
    assert "User: hi" in ctx
    assert "NEXA: hello!" in ctx


def test_history_empty_for_unknown_session(memory):
    assert memory.get_history("does-not-exist") == []
