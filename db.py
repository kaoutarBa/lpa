"""SQLite schema and logging helpers. The db file is created on first use."""
import sqlite3
import uuid
from datetime import datetime, timezone

DB_PATH = "lpa.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    started_at TEXT,
    ended_at TEXT,
    mode TEXT,
    variant TEXT,
    completed INTEGER DEFAULT 0,
    completed_alone INTEGER DEFAULT 0,
    consent INTEGER DEFAULT 0,
    age_range TEXT,
    education TEXT,
    is_simulated INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    ts TEXT,
    step TEXT,
    type TEXT,
    detail TEXT
);
CREATE TABLE IF NOT EXISTS turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    ts TEXT,
    step TEXT,
    speaker TEXT,
    text TEXT,
    source TEXT,
    latency_ms INTEGER
);
CREATE TABLE IF NOT EXISTS analyses (
    session_id TEXT PRIMARY KEY,
    json TEXT
);
"""


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect():
    return sqlite3.connect(DB_PATH)


def init_db():
    with connect() as conn:
        conn.executescript(SCHEMA)


def create_session(consent=1):
    session_id = str(uuid.uuid4())
    with connect() as conn:
        conn.execute(
            "INSERT INTO sessions (id, started_at, consent) VALUES (?, ?, ?)",
            (session_id, now(), consent),
        )
    return session_id


def update_session(session_id, **fields):
    """Set any sessions columns, e.g. update_session(sid, mode="alone")."""
    if not fields:
        return
    cols = ", ".join(f"{name} = ?" for name in fields)
    with connect() as conn:
        conn.execute(f"UPDATE sessions SET {cols} WHERE id = ?", (*fields.values(), session_id))


def log_event(session_id, step, type, detail=""):
    with connect() as conn:
        conn.execute(
            "INSERT INTO events (session_id, ts, step, type, detail) VALUES (?, ?, ?, ?, ?)",
            (session_id, now(), step, type, detail),
        )
