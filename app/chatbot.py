"""
NexaChatbot: ties together memory, intent detection, tools, RAG and
the LLM client. This is the single entry point used by BOTH the CLI
and the FastAPI backend, so behaviour stays identical across them.
"""

from typing import Optional

from .memory import ConversationMemory
from .intents import IntentDetector, Intent
from .tools import safe_calculate, get_datetime_info, CalculatorError
from .rag import document_store
from .llm import llm_client
from .fallback import get_fallback_reply, get_greeting_reply, time_based_greeting
from .logger import get_logger

log = get_logger(__name__)


class NexaChatbot:
    def __init__(self, db_path: str = None):
        self.memory = ConversationMemory(db_path=db_path)
        self.intents = IntentDetector()

    # ---- session helpers --------------------------------------------------

    def start_session(
        self,
        user_name: str,
        session_id: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> str:
        return self.memory.create_session(user_name, session_id=session_id, user_id=user_id)

    def greeting(self, user_name: str) -> str:
        return f"{time_based_greeting(user_name)}!\nWelcome to NEXA AI Chatbot."

    def load_document(self, session_id: str, text: str) -> int:
        """Index a document's text for this session; returns chunk count."""
        return document_store.add_document(session_id, text)

    # ---- main entry point ---------------------------------------------------

    def handle_message(self, session_id: str, user_name: str, user_input: str) -> str:
        user_input = (user_input or "").strip()
        if not user_input:
            return "Please type something so I can help."

        self.memory.add_message(session_id, "user", user_input)
        intent = self.intents.detect(user_input)
        log.info("session=%s intent=%s", session_id, intent)

        reply = self._route(session_id, user_name, user_input, intent)

        self.memory.add_message(session_id, "bot", reply)
        return reply

    # ---- routing --------------------------------------------------------------

    def _route(self, session_id: str, user_name: str, user_input: str, intent: Intent) -> str:
        if intent == Intent.FAREWELL:
            return f"Bye {user_name}! Have a great day."

        if intent == Intent.GREETING:
            return get_greeting_reply(user_name)

        if intent == Intent.CALCULATION:
            expr = self.intents.extract_expression(user_input.lower())
            try:
                result = safe_calculate(expr)
                return f"{expr} = {result}"
            except CalculatorError as exc:
                return f"I couldn't calculate that ({exc})."

        if intent == Intent.DATETIME:
            return get_datetime_info(user_input)

        if intent == Intent.FILE_QUESTION and document_store.has_document(session_id):
            return self._answer_from_document(session_id, user_input)

        # General conversation -> try LLM, else local fallback dictionary.
        history = self.memory.get_context_string(session_id, limit=10)
        llm_reply = llm_client.generate(user_input, history=history)
        if llm_reply:
            return llm_reply

        return get_fallback_reply(user_input)

    def _answer_from_document(self, session_id: str, user_input: str) -> str:
        chunks = document_store.retrieve(session_id, user_input, top_k=3)
        if not chunks:
            return "I couldn't find anything relevant in the uploaded document."

        context = "\n---\n".join(chunks)
        llm_reply = llm_client.generate(user_input, context=context)
        if llm_reply:
            return llm_reply

        # Local fallback mode: no LLM available, just surface the best
        # matching excerpt instead of a generated answer.
        best = chunks[0]
        snippet = best[:400] + ("..." if len(best) > 400 else "")
        return f"Here's the most relevant excerpt I found:\n\n{snippet}"
