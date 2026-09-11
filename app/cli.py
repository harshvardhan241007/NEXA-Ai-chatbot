"""
CLI mode for NEXA AI Chatbot.

Preserves the original nexa.py experience (ask name -> time-based
greeting -> welcome message -> question loop -> 'bye' to exit) while
running on the new modular backend, so calculator/date-time/RAG/LLM
features all work here too.

Extra commands:
  /upload <path>   load a .txt or .pdf file for document Q&A
  /help            show available commands
"""

import time

from .chatbot import NexaChatbot
from .file_reader import load_document, UnsupportedFileType
from .logger import get_logger

log = get_logger(__name__)


def run_cli():
    bot = NexaChatbot()

    name = input("Enter your name: ").strip() or "Friend"
    session_id = bot.start_session(name)

    print(f"\n{bot.greeting(name)}\n")
    time.sleep(0.3)
    print(
        "You can ask me questions, do quick maths (e.g. '12 * 7'), ask "
        "for the date/time, or type '/upload path/to/file.pdf' to load "
        "a document. Type BYE to exit.\n"
    )

    while True:
        user_input = input("You: ").strip()

        if not user_input:
            continue

        if user_input.lower() in {"/help"}:
            print(
                "Commands:\n"
                "  /upload <path>   load a .txt or .pdf document\n"
                "  bye              exit NEXA\n"
            )
            continue

        if user_input.lower().startswith("/upload"):
            parts = user_input.split(maxsplit=1)
            if len(parts) != 2:
                print("Bot: Usage -> /upload path/to/file.pdf")
                continue
            path = parts[1].strip()
            try:
                text = load_document(path)
                n_chunks = bot.load_document(session_id, text)
                print(f"Bot: Document loaded ({n_chunks} chunks indexed). Ask me about it!")
            except (FileNotFoundError, UnsupportedFileType) as exc:
                print(f"Bot: Couldn't load that file - {exc}")
            except Exception as exc:  # noqa: BLE001
                log.exception("Failed to load document")
                print(f"Bot: Something went wrong reading that file - {exc}")
            continue

        reply = bot.handle_message(session_id, name, user_input)
        print(f"Bot: {reply}")

        if user_input.lower() in {"bye", "goodbye", "exit", "quit"}:
            break


if __name__ == "__main__":
    run_cli()
