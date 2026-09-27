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
- Uses NVIDIA Build first with BUILD_ANALYSIS_MODEL (falls back to BUILD_MODEL), then COACH_ORDER. If no provider is configured we fall back to simple
  rules, so the dashboard still shows something honest (and says the source).
"""
import json
import re

import db
from coach import chat, clean_values, parse_json

THEMES = ["otp_meaning", "fear_losing_money", "where_reference", "code_sharing", "fees", "navigation", "other"]
STEP_NAMES = {"home": "Accueil", "biller": "Facturier", "reference": "Référence",
              "confirm": "Confirmation", "otp": "Code SMS"}

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

INSIGHTS_PROMPT = """You are a product analyst for a mobile wallet. Below are AGGREGATED results of test \
sessions where older users learned to pay a bill: a 1st attempt with a voice coach (Salma), then a 2nd attempt \
alone. "Struggling" on a screen = an error, a help request, "I'm lost", a question, or a 20 s hesitation.
At the end of the call people also answered a few questions (understood, feel able to pay alone, feel safe with
the SMS code, hardest step, will try with a real bill): compare what they say with what they did.

Give AT MOST 3 recommendations in French, each one a concrete decision for the wallet product team, most \
important first. Prefer screens where people still struggle in the 2nd attempt (the app must change there); \
a drop between attempts means the coaching works. Hard rules:
- Every item's "evidence" MUST cite at least one number that appears in the data below. No number, no recommendation.
- Do not invent numbers. Do not extrapolate beyond the data. Be factual, short, and not exaggerated.
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
        answers = dict(conn.execute("SELECT question, answer FROM feedback WHERE session_id = ?", (session_id,)))
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
        "end_of_call_answers": answers,
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
        text, provider, latency = chat([{"role": "user", "content": prompt}], max_tokens=1500,
                                       temperature=0.1, timeout=30, purpose="analysis")
        if text is None:
            result = _rules_session(metrics)
        else:
            try:
                result = clean_values(parse_json(text))
                if not isinstance(result, dict):
                    raise ValueError("not a JSON object")
                result["question_themes"] = [t for t in result.get("question_themes", []) if t in THEMES]
                result["completed_alone"] = metrics["completed_alone"]  # the truth comes from our data
                result["source"] = provider
                result["latency_ms"] = latency
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
    """No AI available: deterministic recommendations from the same numbers."""
    n = data["n_sessions"]
    conf = "low" if n < 10 else "medium"
    items = []
    steps = data.get("sessions_struggling_by_step", {})
    still = {k: v["alone"] for k, v in steps.items() if v["alone"]["reached"] and v["alone"]["blocked"]}
    if still:
        step, v = max(still.items(), key=lambda kv: kv[1]["blocked"] / kv[1]["reached"])
        items.append({
            "finding": f"L'écran « {step} » bloque encore au 2e essai.",
            "evidence": f"{v['blocked']} sur {v['reached']} sessions en difficulté sur cet écran quand ils sont seuls.",
            "why": "La difficulté reste après l'accompagnement : elle vient de l'écran lui-même.",
            "action": f"Simplifier l'écran « {step} » (texte plus court, explication visible sur l'écran).",
            "how_to_verify": "Ce chiffre doit baisser au 2e essai sur les prochaines sessions.",
            "confidence": conf, "n_sessions": v["reached"],
        })
    g, a = data.get("help_needed_per_person_attempt1_vs_attempt2", [0, 0])
    pairs = data.get("n_sessions_with_both_attempts", 0)
    if pairs >= 3 and a < g:
        items.append({
            "finding": "Une séance avec Salma réduit l'aide nécessaire.",
            "evidence": f"Aides et relances par personne : {g} au 1er essai, {a} au 2e (n = {pairs}).",
            "why": "Un premier passage guidé suffit pour retenir les étapes.",
            "action": "Proposer la séance guidée aux clients qui paient encore en espèces, avant leur 1er paiement.",
            "how_to_verify": "Suivre le taux de 1er vrai paiement des personnes guidées à 30 jours.",
            "confidence": "low" if pairs < 10 else conf, "n_sessions": pairs,
        })
    said = data.get("self_reported_end_of_call", {})
    trust = said.get("Se sentent en sécurité avec le code SMS")
    if trust and trust["answered"] >= 3 and trust["yes"] * 2 < trust["answered"]:
        items.append({
            "finding": "Le code SMS inquiète encore.",
            "evidence": f"{trust['yes']} sur {trust['answered']} disent se sentir en sécurité avec le code SMS.",
            "why": "La peur de l'arnaque ou de perdre de l'argent freine l'adoption.",
            "action": "Afficher sur l'écran du code : « Ce code n'envoie pas d'argent. Ne le donnez à personne. »",
            "how_to_verify": "La part de « oui » à cette question doit monter.",
            "confidence": "low" if trust["answered"] < 10 else conf, "n_sessions": trust["answered"],
        })
    ab = data.get("abandons", {})
    if ab.get("count"):
        step, count = max(ab["steps"].items(), key=lambda kv: kv[1])
        items.append({
            "finding": "Des abandons se concentrent sur un écran.",
            "evidence": f"{ab['count']} abandons sur {n} sessions, dont {count} à l'écran « {step} ».",
            "why": "La personne ne sait pas comment continuer.",
            "action": f"Ajouter une aide visible et un bouton d'appel sur l'écran « {step} ».",
            "how_to_verify": "Le nombre d'abandons à cet écran doit baisser.",
            "confidence": conf, "n_sessions": n,
        })
    return items[:3]


def cross_session_insights(data, quotes):
    """Evidence-based recommendations. Returns (items, source)."""
    n = data["n_sessions"]
    data_text = json.dumps(data, ensure_ascii=False)
    prompt = INSIGHTS_PROMPT.format(data=data_text, quotes="\n".join(f"- « {q} »" for q in quotes[:8]) or "(aucune)")
    text, provider, _ = chat([{"role": "user", "content": prompt}], max_tokens=2500, temperature=0.2,
                             timeout=40, purpose="analysis")
    if text is None:
        return _rules_insights(data), "rules"
    try:
        items = clean_values(parse_json(text))
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
    return (kept[:3], provider) if kept else (_rules_insights(data), "rules")
