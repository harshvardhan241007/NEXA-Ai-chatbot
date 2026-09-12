"""
Conversation memory: persists chat history per session in SQLite and
exposes helpers to build short-term context for the LLM.
"""

import uuid
from typing import List, Dict, Optional
from .database import get_connection, init_db
from .logger import get_logger

log = get_logger(__name__)


class ConversationMemory:
    def __init__(self, db_path: str = None):
        self.db_path = db_path
        init_db(db_path)

    # ---- session management -------------------------------------------------

    def create_session(
        self,
        user_name: str,
        session_id: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> str:
        session_id = session_id or str(uuid.uuid4())
        with get_connection(self.db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO conversations (session_id, user_id, user_name) "
                "VALUES (?, ?, ?)",
                (session_id, user_id, user_name),
            )
        log.info("Session created/resumed: %s (user=%s)", session_id, user_name)
        return session_id

    def _conversation_id(self, conn, session_id: str) -> Optional[int]:
        row = conn.execute(
            "SELECT id FROM conversations WHERE session_id = ?", (session_id,)
        ).fetchone()
        return row["id"] if row else None

    def get_session_owner(self, session_id: str) -> Optional[int]:
        """Return the user_id that owns this session, or None if the
        session doesn't exist yet or was created before auth existed."""
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT user_id FROM conversations WHERE session_id = ?", (session_id,)
            ).fetchone()
        return row["user_id"] if row else None

    # ---- messages -------------------------------------------------------------

    def add_message(self, session_id: str, role: str, content: str) -> None:
        with get_connection(self.db_path) as conn:
            conv_id = self._conversation_id(conn, session_id)
            if conv_id is None:
                conn.execute(
                    "INSERT INTO conversations (session_id) VALUES (?)",
                    (session_id,),
                )
                conv_id = self._conversation_id(conn, session_id)
            conn.execute(
                "INSERT INTO messages (conversation_id, role, content) "
                "VALUES (?, ?, ?)",
                (conv_id, role, content),
            )

    def get_history(self, session_id: str, limit: int = 20) -> List[Dict]:
        with get_connection(self.db_path) as conn:
            conv_id = self._conversation_id(conn, session_id)
            if conv_id is None:
                return []
            rows = conn.execute(
                "SELECT role, content, created_at FROM messages "
                "WHERE conversation_id = ? ORDER BY id DESC LIMIT ?",
                (conv_id, limit),
            ).fetchall()
        return [dict(r) for r in reversed(rows)]

    def get_context_string(self, session_id: str, limit: int = 10) -> str:
        """Compact text block used as short-term memory in LLM prompts."""
        history = self.get_history(session_id, limit=limit)
        lines = []
        for m in history:
            speaker = "User" if m["role"] == "user" else "NEXA"
            lines.append(f"{speaker}: {m['content']}")
        return "\n".join(lines)
