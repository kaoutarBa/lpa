"""SQLite schema and logging helpers. The db file is created on first use."""
import sqlite3
import uuid
from datetime import datetime, timezone

DB_PATH = "lpa.db"

# table -> columns (name, type). Missing columns are added to an existing db on startup.
TABLES = {
    "sessions": [
        ("id", "TEXT PRIMARY KEY"), ("started_at", "TEXT"), ("ended_at", "TEXT"),
        ("mode_reached", "TEXT"), ("variant", "TEXT"), ("completed", "INTEGER DEFAULT 0"),
        ("completed_alone", "INTEGER DEFAULT 0"), ("consent", "INTEGER DEFAULT 0"),
        ("age_range", "TEXT"), ("education", "TEXT"), ("occupation", "TEXT"), ("is_simulated", "INTEGER DEFAULT 0"),
    ],
    "events": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"), ("session_id", "TEXT"), ("ts", "TEXT"),
        ("mode", "TEXT"), ("step", "TEXT"), ("type", "TEXT"), ("detail", "TEXT"),
    ],
    "turns": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"), ("session_id", "TEXT"), ("ts", "TEXT"),
        ("mode", "TEXT"), ("step", "TEXT"), ("speaker", "TEXT"), ("text", "TEXT"),
        ("input_type", "TEXT"), ("provider", "TEXT"), ("latency_ms", "INTEGER"), ("highlight", "TEXT"),
    ],
    "analyses": [("session_id", "TEXT PRIMARY KEY"), ("json", "TEXT")],
}

MODES = ["learn", "coached", "alone", "done"]


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect():
    return sqlite3.connect(DB_PATH)


def init_db():
    with connect() as conn:
        for table, cols in TABLES.items():
            conn.execute(f"CREATE TABLE IF NOT EXISTS {table} ({', '.join(f'{n} {t}' for n, t in cols)})")
            existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
            for name, typ in cols:
                if name not in existing:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {typ.replace('PRIMARY KEY', '')}")


def create_session(consent=1):
    session_id = str(uuid.uuid4())
    with connect() as conn:
        conn.execute(
            "INSERT INTO sessions (id, started_at, consent) VALUES (?, ?, ?)",
            (session_id, now(), consent),
        )
    return session_id


def update_session(session_id, **fields):
    """Set any sessions columns, e.g. update_session(sid, mode_reached="alone")."""
    if not fields:
        return
    cols = ", ".join(f"{name} = ?" for name in fields)
    with connect() as conn:
        conn.execute(f"UPDATE sessions SET {cols} WHERE id = ?", (*fields.values(), session_id))


def log_event(session_id, mode, step, type, detail=""):
    with connect() as conn:
        conn.execute(
            "INSERT INTO events (session_id, ts, mode, step, type, detail) VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, now(), mode, step, type, detail),
        )


def log_turn(session_id, mode, step, speaker, text, input_type, provider=None, latency_ms=None, highlight=None):
    with connect() as conn:
        conn.execute(
            "INSERT INTO turns (session_id, ts, mode, step, speaker, text, input_type, provider, latency_ms, highlight)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (session_id, now(), mode, step, speaker, text, input_type, provider, latency_ms, highlight),
        )


def count_events(session_id, types, mode=None):
    marks = ", ".join("?" for _ in types)
    sql = f"SELECT COUNT(*) FROM events WHERE session_id = ? AND type IN ({marks})"
    args = [session_id, *types]
    if mode:
        sql += " AND mode = ?"
        args.append(mode)
    with connect() as conn:
        return conn.execute(sql, args).fetchone()[0]
