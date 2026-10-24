"""Database-backed accounts and opt-in encrypted educational chat history.

This is a single-instance starter implementation, not a certified medical
record system. Conversation bodies are only stored after explicit opt-in and
only when a Fernet encryption key has been configured.
"""

import base64
import hashlib
import hmac
import json
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

SESSION_COOKIE = "medguide_session"
SESSION_TTL_SECONDS = 60 * 60 * 24 * 14


def _connect():
    if settings.database_url:
        import psycopg
        from psycopg.rows import dict_row

        database_url = settings.database_url
        if database_url.startswith("postgres://"):
            database_url = "postgresql://" + database_url.removeprefix("postgres://")
        return psycopg.connect(database_url, row_factory=dict_row, connect_timeout=10)
    path = Path(settings.database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _execute(db, statement, parameters=()):
    if settings.database_url:
        statement = statement.replace("?", "%s")
    return db.execute(statement, parameters)


@contextmanager
def _database():
    connection = _connect()
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_account_store():
    with _database() as db:
        body_type = "BYTEA" if settings.database_url else "BLOB"
        statements = (
            """CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                history_enabled INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                expires_at INTEGER NOT NULL
            )""",
            "CREATE INDEX IF NOT EXISTS sessions_expiry ON sessions(expires_at)",
            f"""CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                body {body_type} NOT NULL,
                created_at INTEGER NOT NULL
            )""",
            "CREATE INDEX IF NOT EXISTS conversations_owner_time "
            "ON conversations(user_id, created_at DESC)",
        )
        for statement in statements:
            _execute(db, statement)


def _password_hash(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    derived = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(derived).decode()}"


def _password_matches(password, stored):
    try:
        method, encoded_salt, encoded_hash = stored.split("$", 2)
        if method != "scrypt":
            return False
        salt = base64.urlsafe_b64decode(encoded_salt.encode())
        expected = base64.urlsafe_b64decode(encoded_hash.encode())
        actual = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_account(email, password):
    normalized = email.strip().casefold()
    if len(password) < 12:
        raise ValueError("Choose a password with at least 12 characters.")
    user = {"id": secrets.token_urlsafe(18), "email": normalized, "history_enabled": False}
    try:
        with _database() as db:
            _execute(
                db,
                "INSERT INTO users(id,email,password_hash,history_enabled,created_at) VALUES(?,?,?,?,?)",
                (user["id"], normalized, _password_hash(password), 0, int(time.time())),
            )
    except Exception as exc:
        if isinstance(exc, sqlite3.IntegrityError) or getattr(exc, "sqlstate", None) == "23505":
            raise ValueError("An account with this email already exists.") from None
        raise
    return user


def authenticate(email, password):
    normalized = email.strip().casefold()
    with _database() as db:
        row = _execute(db, "SELECT * FROM users WHERE email=?", (normalized,)).fetchone()
    if row is None or not _password_matches(password, row["password_hash"]):
        return None
    return {"id": row["id"], "email": row["email"], "history_enabled": bool(row["history_enabled"])}


def create_session(user_id):
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("ascii")).hexdigest()
    now = int(time.time())
    with _database() as db:
        _execute(db, "DELETE FROM sessions WHERE expires_at < ?", (now,))
        _execute(
            db,
            "INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)",
            (token_hash, user_id, now + SESSION_TTL_SECONDS),
        )
    return token


def get_user_for_session(token):
    if not token:
        return None
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = int(time.time())
    with _database() as db:
        row = _execute(
            db,
            "SELECT users.id,users.email,users.history_enabled FROM sessions "
            "JOIN users ON users.id=sessions.user_id "
            "WHERE sessions.token_hash=? AND sessions.expires_at>=?",
            (token_hash, now),
        ).fetchone()
    if row is None:
        return None
    return {"id": row["id"], "email": row["email"], "history_enabled": bool(row["history_enabled"])}


def revoke_session(token):
    if token:
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        with _database() as db:
            _execute(db, "DELETE FROM sessions WHERE token_hash=?", (token_hash,))


def set_history_enabled(user_id, enabled):
    with _database() as db:
        _execute(db, "UPDATE users SET history_enabled=? WHERE id=?", (int(enabled), user_id))
        if not enabled:
            _execute(db, "DELETE FROM conversations WHERE user_id=?", (user_id,))


def _cipher():
    key = settings.data_encryption_key.strip()
    if not key:
        raise RuntimeError("Encrypted history is unavailable until DATA_ENCRYPTION_KEY is configured.")
    try:
        return Fernet(key.encode("ascii"))
    except (ValueError, UnicodeEncodeError):
        raise RuntimeError("DATA_ENCRYPTION_KEY is invalid; generate a Fernet key and restart the app.") from None


def ensure_encryption_available():
    _cipher()


def save_conversation(user_id, question, result):
    cipher = _cipher()
    body = json.dumps({"question": question, "result": result}, ensure_ascii=False).encode("utf-8")
    encrypted = cipher.encrypt(body)
    with _database() as db:
        row = _execute(db, "SELECT history_enabled FROM users WHERE id=?", (user_id,)).fetchone()
        if row is None or not row["history_enabled"]:
            return
        _execute(
            db,
            "INSERT INTO conversations(id,user_id,body,created_at) VALUES(?,?,?,?)",
            (secrets.token_urlsafe(18), user_id, encrypted, int(time.time())),
        )


def list_conversations(user_id, limit=50):
    cipher = _cipher()
    with _database() as db:
        rows = _execute(
            db,
            "SELECT id,body,created_at FROM conversations WHERE user_id=? "
            "ORDER BY created_at DESC LIMIT ?",
            (user_id, min(max(limit, 1), 100)),
        ).fetchall()
    result = []
    for row in rows:
        try:
            body = json.loads(cipher.decrypt(row["body"]).decode("utf-8"))
        except (InvalidToken, ValueError, UnicodeDecodeError):
            continue
        result.append({"id": row["id"], "created_at": row["created_at"], **body})
    return result


def delete_account(user_id):
    with _database() as db:
        _execute(db, "DELETE FROM users WHERE id=?", (user_id,))
