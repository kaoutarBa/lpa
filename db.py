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
        ("age_range", "TEXT"), ("education", "TEXT"), ("is_simulated", "INTEGER DEFAULT 0"),
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


# ---------------- Simulated sessions (dev helper, always is_simulated = 1) ----------------
SIM_QUESTIONS = {
    "otp_meaning": ("otp", ["C'est quoi ce code ?", "Le code sert à quoi ?", "Pourquoi on m'envoie un SMS ?"]),
    "fear_losing_money": ("confirm", ["Si je me trompe, je perds mon argent ?", "L'argent part tout de suite ?"]),
    "where_reference": ("reference", ["Où est le numéro de la facture ?", "Je ne trouve pas la référence"]),
    "code_sharing": ("otp", ["Je dois donner ce code à quelqu'un ?"]),
    "fees": ("confirm", ["Il y a des frais ?"]),
}


def generate_simulated_sessions(n=10, seed=None):
    """Insert n realistic fake sessions (always is_simulated = 1)."""
    import json
    import random
    from datetime import timedelta

    rnd = random.Random(seed)
    with connect() as conn:
        for i in range(n):
            sid = str(uuid.uuid4())
            t = datetime.now(timezone.utc) - timedelta(hours=rnd.uniform(1, 48))
            events, turns, themes, struggles = [], [], {}, []

            def ev(mode, step, type, detail="", secs=(3, 12)):
                nonlocal t
                t += timedelta(seconds=rnd.uniform(*secs))
                events.append((sid, t.isoformat(timespec="seconds"), mode, step, type, detail))

            def ask(mode, theme):
                step, questions = SIM_QUESTIONS[theme]
                if mode == "alone":  # in alone mode every question is a help request
                    ev(mode, step, "help_request", "text")
                question = rnd.choice(questions)
                turns.append((sid, t.isoformat(timespec="seconds"), mode, step, "user", question,
                              rnd.choice(["voice", "text"]), None, None, None))
                themes[theme] = question

            for k in range(3):
                ev("learn", "lesson", "step_enter", f"lesson_{k + 1}", (8, 20))
            reached = "learn"
            otp_friction = 0.45
            if rnd.random() < 0.95:
                reached = "coached"
                for step in ["home", "biller", "reference", "confirm", "otp", "receipt"]:
                    ev("coached", step, "step_enter")
                    if step == "reference" and rnd.random() < 0.35:
                        ev("coached", step, "error_reference", "EL-4471")
                        ask("coached", "where_reference") if rnd.random() < 0.5 else None
                    if step == "confirm" and rnd.random() < 0.3:
                        ask("coached", rnd.choice(["fear_losing_money", "fees"]))
                    if step == "otp" and rnd.random() < otp_friction:
                        ev("coached", step, "error_otp", "48")
                        ask("coached", rnd.choice(["otp_meaning", "code_sharing"]))
                ev("coached", "otp", "complete")
            slips, alone_ok = 0, False
            if reached == "coached" and rnd.random() < 0.85:
                reached = "alone"
                ev("alone", "home", "step_enter")
                for step in ["biller", "reference", "confirm", "otp"]:
                    ev("alone", step, "step_enter", secs=(5, 22))
                    if step == "otp" and rnd.random() < otp_friction:
                        ev("alone", step, "error_otp", "48")
                        slips += 1
                        if rnd.random() < 0.7:
                            ask("alone", "otp_meaning")
                            slips += 1
                    if step == "reference" and rnd.random() < 0.15:
                        ev("alone", step, "lost")
                        slips += 1
                if rnd.random() < 0.85:
                    ev("alone", "otp", "complete")
                    reached, alone_ok = "done", slips == 0
                    ev("done", "done", "step_enter", secs=(1, 2))
                if slips:
                    struggles.append({"step": "otp", "reason": "Hésitation sur le rôle du code SMS."})
            conn.execute(
                "INSERT INTO sessions (id, started_at, ended_at, mode_reached, completed, completed_alone,"
                " consent, age_range, education, is_simulated) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, 1)",
                (sid, events[0][1], t.isoformat(timespec="seconds") if reached == "done" else None, reached,
                 int(reached == "done"), int(alone_ok),
                 rnd.choice(["50 – 64 ans", "65 ans et plus", "30 – 49 ans", None]),
                 rnd.choice(["Pas d'école", "Primaire", "Collège / Lycée", None])),
            )
            conn.executemany(
                "INSERT INTO events (session_id, ts, mode, step, type, detail) VALUES (?, ?, ?, ?, ?, ?)", events
            )
            conn.executemany(
                "INSERT INTO turns (session_id, ts, mode, step, speaker, text, input_type, provider, latency_ms,"
                " highlight) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", turns,
            )
            analysis = {
                "struggle_steps": struggles,
                "question_themes": sorted(themes),
                "theme_quotes": themes,
                "confidence": "confident" if alone_ok else rnd.choice(["hesitant", "improving"]),
                "completed_alone": alone_ok,
                "recommendation": "Expliquer plus tôt que le code SMS n'envoie pas d'argent." if struggles else "",
                "simulated": True,
            }
            conn.execute("INSERT INTO analyses (session_id, json) VALUES (?, ?)", (sid, json.dumps(analysis)))


def delete_simulated_sessions():
    with connect() as conn:
        ids = "SELECT id FROM sessions WHERE is_simulated = 1"
        for table in ("events", "turns", "analyses"):
            conn.execute(f"DELETE FROM {table} WHERE session_id IN ({ids})")
        conn.execute("DELETE FROM sessions WHERE is_simulated = 1")
