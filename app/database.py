"""
SQLite persistence layer.

Two tables:
  conversations(id, session_id, user_name, created_at)
  messages(id, conversation_id, role, content, created_at)
"""

import sqlite3
import os
from contextlib import contextmanager
from .config import settings
from .logger import get_logger

log = get_logger(__name__)


def _ensure_dir(path: str) -> None:
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)


@contextmanager
def get_connection(db_path: str = None):
    """Yield a SQLite connection with foreign keys enabled.

    Pass db_path=':memory:' for isolated/unit-test databases.
    """
    path = db_path or settings.DB_PATH
    if path != ":memory:":
        _ensure_dir(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: str = None) -> None:
    """Create tables if they do not already exist."""
    with get_connection(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT UNIQUE NOT NULL,
                user_name   TEXT,
                created_at  TEXT DEFAULT (datetime('now'))
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role            TEXT NOT NULL CHECK(role IN ('user','bot')),
                content         TEXT NOT NULL,
                created_at      TEXT DEFAULT (datetime('now')),
                FOREIGN KEY(conversation_id) REFERENCES conversations(id)
            );
            """
        )
    log.info("Database initialized at %s", db_path or settings.DB_PATH)
