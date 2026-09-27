"""Per-session progression: the guided attempt vs the alone attempt, and an autonomy level."""
import pandas as pd

ERROR_TYPES = ["error_reference", "error_otp"]
HELP_TYPES = ["help_request", "lost"]
LEVELS = {4: "4 · Autonome", 3: "3 · Presque seul", 2: "2 · Aidé ponctuellement", 1: "1 · Accompagné",
          0: "Non terminé"}
LEVEL_HELP = {
    4: "a payé seul, sans erreur, sans aide ni relance",
    3: "a payé seul sans aide, mais avec des erreurs ou des relances de Salma",
    2: "a payé seul avec 1 ou 2 aides",
    1: "a payé avec le guidage de Salma (ou 3 aides et plus, ou un tour guidé en plus)",
    0: "n'a pas terminé (étape d'abandon indiquée)",
}
STEP_NAMES = {"lesson": "Leçons", "home": "Accueil", "biller": "Facturier", "reference": "Référence",
              "confirm": "Confirmation", "otp": "Code SMS", "receipt": "Reçu"}


def attempt(ev, tu, mode):
    """Help, errors, idle nudges and duration of one attempt (all events of that mode)."""
    e = ev[ev["mode"] == mode]
    help_ = int(e.type.isin(HELP_TYPES).sum())
    if mode != "alone":  # questions asked while guided; in alone mode they are already help_request events
        help_ += int(((tu["mode"] == mode) & (tu.speaker == "user")).sum())
    done = e[e.type == "complete"]
    secs = None
    if not done.empty:
        end = done.t.iloc[-1]
        starts = e[(e.type == "step_enter") & (e.step == "home") & (e.t <= end)]
        if not starts.empty:
            secs = (end - starts.t.iloc[-1]).total_seconds()
    return {
        "started": bool((e.type == "step_enter").any()),
        "done": not done.empty,
        "help": help_,
        "errors": int(e.type.isin(ERROR_TYPES).sum()),
        "nudges": int((e.type == "idle_nudge").sum()),
        "secs": secs,
    }


def sessions_progress(sessions, events, turns):
    """One row per session: stats of both attempts, autonomy level, abandon step."""
    events = events.assign(t=pd.to_datetime(events.ts, utc=True, format="ISO8601")).sort_values("t")
    ev_by, tu_by = dict(tuple(events.groupby("session_id"))), dict(tuple(turns.groupby("session_id")))
    empty_ev, empty_tu = events.iloc[0:0], turns.iloc[0:0]
    rows = []
    for sid in sessions.id:
        ev, tu = ev_by.get(sid, empty_ev), tu_by.get(sid, empty_tu)
        g, a = attempt(ev, tu, "coached"), attempt(ev, tu, "alone")
        repeat = bool((ev.type == "repeat_coached").any())
        if a["done"]:
            if repeat or a["help"] >= 3:
                level = 1
            elif a["help"] >= 1:
                level = 2
            elif a["errors"] or a["nudges"]:
                level = 3
            else:
                level = 4
        elif g["done"] and not a["started"]:
            level = 1
        else:
            level = 0
        entered = ev[ev.type == "step_enter"]
        abandon = entered.step.iloc[-1] if level == 0 and not entered.empty else None
        rows.append({
            "session_id": sid, "level": level, "abandon_step": abandon, "both_done": g["done"] and a["done"],
            **{f"g_{k}": v for k, v in g.items()}, **{f"a_{k}": v for k, v in a.items()},
        })
    return pd.DataFrame(rows)


def share(k, n):
    """'3 sur 5' under 10 sessions, a percentage from 10 on."""
    return f"{k} sur {n}" if n < 10 else f"{k / n:.0%}"
