"""AI analysis: one JSON summary per session, and evidence-based recommendations across sessions.

How the AI part works:
- analyze_session: we send the LLM the transcript (what the user asked, what Salma said) plus the
  session's numbers (errors and help per step), and require a strict JSON answer. The LLM is good at
  reading free text ("Si je me trompe, je perds mon argent ?") and labelling it with a theme
  (fear_losing_money); the numbers themselves come from our database, not from the model.
- cross_session_insights: we send only aggregated numbers + a few short anonymous quotes (never raw
  transcripts). The prompt says "no number, no recommendation", and we also enforce it in code:
  an item whose evidence cites no number present in the data is dropped. With fewer than 10 sessions
  the confidence is forced to "low".
- Same provider chain as the coach (coach.chat). If no provider is configured we fall back to simple
  rules, so the dashboard still shows something honest (and says the source).
"""
import json
import re

import db
from coach import chat, parse_json

THEMES = ["otp_meaning", "fear_losing_money", "where_reference", "code_sharing", "fees", "navigation", "other"]
STEP_NAMES = {"home": "accueil", "biller": "choix du facturier", "reference": "référence",
              "confirm": "confirmation", "otp": "code SMS"}

SESSION_PROMPT = """You analyse ONE anonymous practice session of an older person learning to pay a bill \
in a practice mobile wallet, guided by a voice coach (Salma). Modes: learn (lessons), coached (guided), \
alone (trying alone), done (paid alone).

Return JSON only, with exactly these keys:
{{"struggle_steps": [{{"step": "<home|biller|reference|confirm|otp>", "reason": "<short French reason>"}}],
 "question_themes": ["<themes from: {themes}>"],
 "theme_quotes": {{"<theme>": "<one short exact quote of the user for that theme>"}},
 "confidence": "hesitant | improving | confident",
 "completed_alone": true/false,
 "recommendation": "<one short French sentence for the wallet product team>"}}
Base everything on the data below only. Use an empty list when nothing applies.

Session metrics:
{metrics}

Transcript:
{transcript}"""

INSIGHTS_PROMPT = """You are a product analyst for a mobile wallet. Below are AGGREGATED results of practice \
sessions where older users learned to pay a bill, plus a few short anonymous quotes.

Write 3 to 5 findings in French. Hard rules:
- Every item's "evidence" MUST cite at least one number that appears in the data below. No number, no recommendation.
- Do not invent numbers. Do not extrapolate beyond the data.
- "confidence" is "low" if n_sessions < 10, otherwise low/medium/high depending on sample size and effect size.
- "n_sessions" is the number of sessions behind the finding.

Return a JSON list only:
[{{"finding": "...", "evidence": "...", "why": "...", "action": "...", "how_to_verify": "...", \
"confidence": "low | medium | high", "n_sessions": 0}}]

Data:
{data}

Quotes:
{quotes}"""


def _session_data(session_id):
    with db.connect() as conn:
        mode_reached, completed_alone = conn.execute(
            "SELECT mode_reached, completed_alone FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        events = conn.execute("SELECT mode, step, type FROM events WHERE session_id = ?", (session_id,)).fetchall()
        turns = conn.execute(
            "SELECT mode, step, speaker, text FROM turns WHERE session_id = ? ORDER BY id", (session_id,)
        ).fetchall()
    per_step = {}
    for mode, step, type in events:
        if type in ("error_reference", "error_otp", "help_request", "lost"):
            key = "errors" if type.startswith("error") else "help"
            per_step.setdefault(step, {"errors": 0, "help": 0})[key] += 1
    metrics = {
        "mode_reached": mode_reached,
        "completed_alone": bool(completed_alone),
        "errors_and_help_per_step": per_step,
        "user_questions": sum(1 for t in turns if t[2] == "user"),
        "repeat_coached": sum(1 for e in events if e[2] == "repeat_coached"),
    }
    return metrics, turns


def _rules_session(metrics):
    """No AI available: a minimal honest analysis from the numbers only."""
    per_step = metrics["errors_and_help_per_step"]
    struggles = [{"step": s, "reason": f"{v['errors']} erreur(s), {v['help']} aide(s)"}
                 for s, v in sorted(per_step.items(), key=lambda kv: -sum(kv[1].values()))]
    slips = sum(sum(v.values()) for v in per_step.values())
    return {
        "struggle_steps": struggles[:2],
        "question_themes": [],
        "confidence": "confident" if metrics["completed_alone"] else ("improving" if slips < 3 else "hesitant"),
        "completed_alone": metrics["completed_alone"],
        "recommendation": "",
        "source": "rules",
    }


def analyze_session(session_id):
    """Analyse one session and store the JSON in `analyses`. Never raises."""
    try:
        metrics, turns = _session_data(session_id)
        transcript = "\n".join(
            f"[{mode}/{step}] {'Utilisateur' if speaker == 'user' else 'Salma'}: {text}"
            for mode, step, speaker, text in turns[-60:]
        )
        prompt = SESSION_PROMPT.format(
            themes=", ".join(THEMES), metrics=json.dumps(metrics, ensure_ascii=False), transcript=transcript
        )
        text, provider, _ = chat([{"role": "user", "content": prompt}], max_tokens=500, temperature=0.1, timeout=20)
        if text is None:
            result = _rules_session(metrics)
        else:
            try:
                result = parse_json(text)
                if not isinstance(result, dict):
                    raise ValueError("not a JSON object")
                result["question_themes"] = [t for t in result.get("question_themes", []) if t in THEMES]
                result["completed_alone"] = metrics["completed_alone"]  # the truth comes from our data
                result["source"] = provider
            except Exception as e:
                result = {"error": f"unparseable answer from {provider}: {e}"}
    except Exception as e:
        result = {"error": str(e)}
    with db.connect() as conn:
        conn.execute("INSERT OR REPLACE INTO analyses (session_id, json) VALUES (?, ?)",
                     (session_id, json.dumps(result, ensure_ascii=False)))
    return result


def _numbers(text):
    return {float(n.replace(",", ".")) for n in re.findall(r"\d+(?:[.,]\d+)?", text)}


def _rules_insights(data):
    """No AI available: deterministic findings from the same numbers."""
    n = data["n_sessions"]
    conf = "low" if n < 10 else "medium"
    items = []
    steps = data["friction_by_step"]
    if steps:
        step, v = max(steps.items(), key=lambda kv: kv[1]["errors"] + kv[1]["help"])
        items.append({
            "finding": f"L'écran « {STEP_NAMES.get(step, step)} » concentre le plus de difficultés.",
            "evidence": f"{v['errors']} erreurs et {v['help']} demandes d'aide sur {n} sessions.",
            "why": "C'est l'étape où les utilisateurs hésitent le plus.",
            "action": "Simplifier le texte de cet écran et y ajouter une explication courte.",
            "how_to_verify": "Comparer erreurs + aides par session avant/après sur le tableau de bord.",
            "confidence": conf, "n_sessions": n,
        })
    otp = data.get("otp_friction_per_session", {})
    if "A" in otp and "B" in otp:
        a, b = otp["A"], otp["B"]
        items.append({
            "finding": "Le texte B de l'écran du code SMS change la friction.",
            "evidence": f"{a['mean']} erreurs + aides par session avec A (n = {a['n']}) contre {b['mean']} avec B (n = {b['n']}).",
            "why": "B explique que le code confirme l'identité et n'envoie pas d'argent.",
            "action": "Adopter le texte B si l'écart se confirme.",
            "how_to_verify": "Test A/B sur plus de sessions réelles.",
            "confidence": "low" if a["n"] + b["n"] < 10 else conf, "n_sessions": a["n"] + b["n"],
        })
    items.append({
        "finding": "Part des testeurs qui paient seuls après une séance.",
        "evidence": f"{data['autonomy_pct']} % des {n} sessions : essai seul réussi sans erreur ni aide.",
        "why": "Mesure directe de l'adoption après accompagnement.",
        "action": "Proposer la séance guidée aux nouveaux clients seniors.",
        "how_to_verify": "Suivre le taux de paiement réel à 30 jours des testeurs.",
        "confidence": conf, "n_sessions": n,
    })
    return items


def cross_session_insights(data, quotes):
    """Evidence-based recommendations. Returns (items, source)."""
    n = data["n_sessions"]
    data_text = json.dumps(data, ensure_ascii=False)
    prompt = INSIGHTS_PROMPT.format(data=data_text, quotes="\n".join(f"- « {q} »" for q in quotes[:8]) or "(aucune)")
    text, provider, _ = chat([{"role": "user", "content": prompt}], max_tokens=1200, temperature=0.2, timeout=25)
    if text is None:
        return _rules_insights(data), "rules"
    try:
        items = parse_json(text)
        items = items if isinstance(items, list) else items.get("items", [])
    except Exception:
        return _rules_insights(data), "rules"
    allowed = _numbers(data_text)
    keys = ["finding", "evidence", "why", "action", "how_to_verify", "confidence", "n_sessions"]
    kept = []
    for item in items:
        if not isinstance(item, dict) or not all(k in item for k in keys):
            continue
        if not (_numbers(str(item["evidence"])) & allowed):
            continue  # no number from the data → no recommendation
        if n < 10 or item["confidence"] not in ("low", "medium", "high"):
            item["confidence"] = "low"
        kept.append(item)
    return (kept, provider) if kept else (_rules_insights(data), "rules")
