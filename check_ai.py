"""Quick live check of the AI setup, using .streamlit/secrets.toml.

Run from the project folder:  python check_ai.py
Makes one coach call and one analysis call and prints the answer, the provider and the latency.
Uses a throwaway database, so lpa.db is not touched.
"""
import json
import os
import tempfile

import analysis
import coach
import db

print("Coach order    :", [p[0] + " / " + p[3] for p in coach.providers()] or "no provider configured")
print("Analysis order :", [p[0] + " / " + p[3] for p in coach.providers("analysis")] or "no provider configured")

print("\n--- Coach call (screen: reference, 2nd mistake) ---")
r = coach.ask(
    "Je ne trouve pas le numéro de référence, il est où ?", "reference", "coached", [],
    last_action="a tapé « EL-44 », ce qui est faux", errors=2,
)
print(f"Salma     : {r['say']}\nHighlight : {r['highlight']}\nProvider  : {r['provider']}\nLatency   : {r['latency_ms']} ms")

print("\n--- Analysis call (one fake session) ---")
db.DB_PATH = os.path.join(tempfile.mkdtemp(), "check.db")
db.init_db()
sid = db.create_session()
db.update_session(sid, mode_reached="done", completed=1, completed_alone=0)
for mode, step, type in [("coached", "reference", "error_reference"), ("coached", "otp", "error_otp"),
                         ("alone", "otp", "help_request")]:
    db.log_event(sid, mode, step, type)
for mode, step, who, text in [
    ("coached", "otp", "user", "C'est quoi ce code ? Il envoie de l'argent ?"),
    ("coached", "otp", "coach", "Non, ce code confirme que c'est bien vous. Il n'envoie pas d'argent."),
    ("alone", "otp", "user", "Si je me trompe, je perds mon argent ?"),
]:
    db.log_turn(sid, mode, step, who, text, "text")
result = analysis.analyze_session(sid)
print(json.dumps(result, ensure_ascii=False, indent=2))
print(f"Provider  : {result.get('source')}\nLatency   : {result.get('latency_ms', '—')} ms")
