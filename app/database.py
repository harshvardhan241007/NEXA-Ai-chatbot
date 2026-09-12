"""
SQLite persistence layer.

Tables:
  users(id, username, password_hash, salt, created_at)
  auth_tokens(token, user_id, created_at)
  conversations(id, session_id, user_id, user_name, created_at)
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


def _column_exists(conn, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table});").fetchall()
    return any(r["name"] == column for r in rows)


def init_db(db_path: str = None) -> None:
    """Create tables if they do not already exist, and migrate older
    databases (e.g. ones created before auth support existed) in place."""
    with get_connection(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                username       TEXT UNIQUE NOT NULL,
                password_hash  TEXT NOT NULL,
                salt           TEXT NOT NULL,
                created_at     TEXT DEFAULT (datetime('now'))
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_tokens (
                token       TEXT PRIMARY KEY,
                user_id     INTEGER NOT NULL,
                created_at  TEXT DEFAULT (datetime('now')),
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT UNIQUE NOT NULL,
                user_id     INTEGER,
                user_name   TEXT,
                created_at  TEXT DEFAULT (datetime('now')),
                FOREIGN KEY(user_id) REFERENCES users(id)
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
        # Migration: databases created before login/signup existed won't
        # have this column yet.
        if not _column_exists(conn, "conversations", "user_id"):
            conn.execute("ALTER TABLE conversations ADD COLUMN user_id INTEGER;")
    log.info("Database initialized at %s", db_path or settings.DB_PATH)
