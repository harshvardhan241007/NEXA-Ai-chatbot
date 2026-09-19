"""
Username/password authentication for NEXA.

Kept dependency-free on purpose (no bcrypt/passlib/pyjwt needed):
  - Passwords are hashed with PBKDF2-HMAC-SHA256 + a random per-user salt.
  - "Sessions" are opaque random tokens stored server-side in the
    auth_tokens table. The client sends the token back on every request
    as `Authorization: Bearer <token>`.
"""

import hashlib
import hmac
import re
import secrets
from typing import Optional

from .database import get_connection
from .logger import get_logger

log = get_logger(__name__)

PBKDF2_ITERATIONS = 260_000
MIN_USERNAME_LEN = 3
MIN_PASSWORD_LEN = 6
MIN_DISPLAY_NAME_LEN = 1

# Common valid public email TLDs. This catches obvious typos such as
# `aman@examples.comm` while still allowing common domains such as .com,
# .in, .org, .net, .io, .ai, .dev, .co.in, etc.
COMMON_EMAIL_TLDS = {
    "com", "in", "org", "net", "edu", "gov", "mil", "int",
    "co", "uk", "us", "ca", "au", "nz", "de", "fr", "it", "es",
    "nl", "be", "ch", "at", "se", "no", "dk", "fi", "pl", "ie",
    "pt", "gr", "cz", "sk", "hu", "ro", "bg", "hr", "si", "rs",
    "ua", "ru", "tr", "il", "ae", "sa", "qa", "pk", "bd", "lk",
    "np", "sg", "my", "id", "ph", "th", "vn", "jp", "kr", "cn",
    "hk", "tw", "za", "ng", "ke", "eg", "br", "mx", "ar", "cl",
    "pe", "co", "ai", "app", "dev", "io", "me", "info", "biz", "xyz",
    "tech", "online", "site", "cloud", "store", "shop", "pro", "name",
    "live", "life", "today", "world", "website", "space", "digital",
    "email", "social", "solutions", "services", "agency", "company",
    "network", "software", "systems", "support", "center", "zone",
    "one", "club", "blog", "news", "media", "academy", "school",
    "travel", "health", "finance", "law", "care", "works", "design",
    "studio", "art", "photography", "video", "games", "guide", "global",
    "group", "today", "top", "vip", "link", "lol", "dev", "cloud",
}

_EMAIL_RE = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$"
)


def _validate_email(username: str) -> str:
    """Validate an email address and return its normalized lowercase form."""
    email = (username or "").strip().lower()

    if len(email) > 254 or not _EMAIL_RE.fullmatch(email):
        raise AuthError("Please enter a valid email address.")

    local_part, domain = email.rsplit("@", 1)

    if len(local_part) > 64:
        raise AuthError("Please enter a valid email address.")

    labels = domain.split(".")
    if len(labels) < 2:
        raise AuthError("Please enter a valid email address.")

    # Require a recognized/common TLD so obvious typos such as `.comm`
    # are rejected instead of being treated as valid email formats.
    tld = labels[-1]
    if tld not in COMMON_EMAIL_TLDS:
        raise AuthError("Please enter a valid email address (for example, name@gmail.com).")

    return email


class AuthError(Exception):
    """Raised for any signup/login failure. Message is safe to show the user."""


def _hash_password(password: str, salt: bytes) -> str:
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return dk.hex()


def signup(
    display_name: str,
    username: str,
    password: str,
    db_path: str = None,
) -> dict:
    display_name = (display_name or "").strip()
    username = _validate_email(username)
    password = password or ""

    if len(display_name) < MIN_DISPLAY_NAME_LEN:
        raise AuthError("Name is required.")

    if len(password) < MIN_PASSWORD_LEN:
        raise AuthError(f"Password must be at least {MIN_PASSWORD_LEN} characters.")

    salt = secrets.token_bytes(16)
    pw_hash = _hash_password(password, salt)

    with get_connection(db_path) as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,),
        ).fetchone()

        if existing:
            raise AuthError("That email is already registered.")

        cur = conn.execute(
            """
            INSERT INTO users (
                username,
                display_name,
                password_hash,
                salt
            )
            VALUES (?, ?, ?, ?)
            """,
            (username, display_name, pw_hash, salt.hex()),
        )
        user_id = cur.lastrowid

    token = _create_token(user_id, db_path)

    log.info("New user signed up: %s", username)

    return {
        "user_id": user_id,
        "username": username,
        "display_name": display_name,
        "token": token,
    }


def login(username: str, password: str, db_path: str = None) -> dict:
    username = (username or "").strip()
    # Emails are case-insensitive for login purposes. Keep compatibility
    # with any older non-email usernames by only lowercasing email-style values.
    if "@" in username:
        username = username.lower()
    password = password or ""

    with get_connection(db_path) as conn:
        row = conn.execute(
            """
            SELECT
                id,
                username,
                display_name,
                password_hash,
                salt
            FROM users
            WHERE username = ?
            """,
            (username,),
        ).fetchone()

    # Same generic error whether the username doesn't exist or the
    # password is wrong -- avoids leaking which usernames are registered.
    if row is None:
        raise AuthError("Invalid email or password.")

    salt = bytes.fromhex(row["salt"])
    expected = _hash_password(password, salt)

    if not hmac.compare_digest(expected, row["password_hash"]):
        raise AuthError("Invalid email or password.")

    # Existing users created before the name feature may have no display_name.
    # Fall back to the email/username local part in that case.
    display_name = (row["display_name"] or "").strip()

    if not display_name:
        if "@" in row["username"]:
            display_name = row["username"].split("@", 1)[0]
        else:
            display_name = row["username"]

    token = _create_token(row["id"], db_path)

    log.info("User logged in: %s", username)

    return {
        "user_id": row["id"],
        "username": row["username"],
        "display_name": display_name,
        "token": token,
    }


def logout(token: str, db_path: str = None) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            "DELETE FROM auth_tokens WHERE token = ?",
            (token,),
        )


def get_user_from_token(
    token: str,
    db_path: str = None,
) -> Optional[dict]:
    if not token:
        return None

    with get_connection(db_path) as conn:
        row = conn.execute(
            """
            SELECT
                u.id AS user_id,
                u.username AS username,
                u.display_name AS display_name
            FROM auth_tokens t
            JOIN users u ON u.id = t.user_id
            WHERE t.token = ?
            """,
            (token,),
        ).fetchone()

    if not row:
        return None

    user = dict(row)

    # Existing users may have NULL display_name.
    if not (user.get("display_name") or "").strip():
        username = user.get("username", "")

        if "@" in username:
            user["display_name"] = username.split("@", 1)[0]
        else:
            user["display_name"] = username

    return user


def _create_token(user_id: int, db_path: str = None) -> str:
    token = secrets.token_hex(32)

    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO auth_tokens (token, user_id) VALUES (?, ?)",
            (token, user_id),
        )

    return token
