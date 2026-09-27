"""Dashboard for the wallet provider: a few numbers that help decide what to fix.

1. Four key figures (autonomy, help needed, main blocking screen, abandons)
2. One chart: where people still struggle, 1st attempt (with Salma) vs 2nd attempt (alone)
3. Why: reasons found by the AI analyses + what people ask
4. What to do: up to 3 evidence-based recommendations
"""
import html
import json
from collections import Counter

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import analysis
import db
from content import UI, inject_css
from progress import STEP_NAMES, blocking_by_step, sessions_progress, share

if not st.session_state.get("provider_view"):  # never shown in the user view (also hidden from the menu)
    st.stop()
st.set_page_config(page_title="Tableau de bord", page_icon="📊", layout="wide")
inject_css()
st.markdown("""<style>.block-container { max-width: 1000px; }
.kpi { border: 1px solid #d8dee9; border-radius: 16px; padding: 14px 16px; height: 100%; }
.kpi .label { font-size: 16px; color: #52514e; }
.kpi .value { font-size: 32px; font-weight: 800; color: #0b0b0b; line-height: 1.2; }
.kpi .sub { font-size: 15px; color: #52514e; }
</style>""", unsafe_allow_html=True)

# Validated categorical slots (light surface) + recessive ink/grid.
BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e6e6e3"
WALLET_STEPS = ["home", "biller", "reference", "confirm", "otp"]


def kpi(col, label, value, sub=""):
    col.markdown(f'<div class="kpi"><div class="label">{label}</div><div class="value">{value}</div>'
                 f'<div class="sub">{sub}</div></div>', unsafe_allow_html=True)


def num(x):
    return f"{x:.1f}".replace(".", ",")


# ---------- load (real sessions only) ----------
with db.connect() as conn:
    s = pd.read_sql("SELECT * FROM sessions WHERE consent = 1 AND mode_reached IS NOT NULL "
                    "AND COALESCE(is_simulated, 0) = 0", conn)
    events = pd.read_sql("SELECT * FROM events", conn)
    turns = pd.read_sql("SELECT * FROM turns", conn)
    analyses = pd.read_sql("SELECT * FROM analyses", conn)
ids = set(s.id)
ev = events[events.session_id.isin(ids)]
tu = turns[turns.session_id.isin(ids)]
N = len(s)

st.title(UI["dashboard_title"])
if N < 3:
    st.info(f"Pas encore assez de données : {N} session(s). Les chiffres apparaissent à partir de 3 sessions.")
    st.stop()
dates = pd.to_datetime(s.started_at, utc=True, format="ISO8601")
st.caption(f"N = {N} sessions de test · du {dates.min():%d/%m} au {dates.max():%d/%m}")

prog = sessions_progress(s, ev, tu)
alone_ok = int((prog.level >= 3).sum())
autonomous = int((prog.level == 4).sum())
pairs = prog[prog.both_done]
n_pairs = len(pairs)
need_g = float((pairs.g_help + pairs.g_nudges).mean()) if n_pairs else 0.0
need_a = float((pairs.a_help + pairs.a_nudges).mean()) if n_pairs else 0.0
blocking = blocking_by_step(ev, tu, WALLET_STEPS)
alone_rates = {k: v["alone"]["blocked"] / v["alone"]["reached"] for k, v in blocking.items() if v["alone"]["reached"]}
top_step = max(alone_rates, key=alone_rates.get) if alone_rates and max(alone_rates.values()) > 0 else None
abandons = prog.abandon_step.dropna()

# ================= 1. Key figures =================
k = st.columns(4)
kpi(k[0], "Paient seuls après une séance", share(alone_ok, N),
    f"dont {autonomous} sans aucune aide ni erreur")
if n_pairs >= 3 and need_g > 0:
    value = f"−{(need_g - need_a) / need_g:.0%}" if n_pairs >= 10 else f"{num(need_g)} → {num(need_a)}"
    kpi(k[1], "Aide nécessaire, 1er → 2e essai", value, f"aides + relances par personne · n = {n_pairs}")
else:
    kpi(k[1], "Aide nécessaire, 1er → 2e essai", "—", "pas encore assez d'essais complets")
if top_step:
    b = blocking[top_step]["alone"]
    kpi(k[2], "Blocage n°1 (essai seul)", STEP_NAMES[top_step], f"{b['blocked']} sur {b['reached']} y bloquent encore")
else:
    kpi(k[2], "Blocage n°1 (essai seul)", "Aucun", "personne ne bloque au 2e essai")
kpi(k[3], "Abandons", share(len(abandons), N),
    f"surtout : {STEP_NAMES.get(abandons.mode().iloc[0], abandons.mode().iloc[0])}" if len(abandons) else "aucun")

# ================= 2. Where people still struggle =================
st.subheader("Où les gens bloquent")
st.caption("Ce qui baisse au 2e essai s'apprend avec Salma. Ce qui reste haut est à corriger dans l'app.")


def rate(step, attempt):
    v = blocking[step][attempt]
    return v["blocked"] / v["reached"] if v["reached"] else 0


def label(step, attempt):
    v = blocking[step][attempt]
    if not v["reached"] or not v["blocked"]:
        return ""
    return f"{v['blocked']}/{v['reached']}" if N < 10 else f"{rate(step, attempt):.0%}"


x = [STEP_NAMES[step] for step in WALLET_STEPS]
fig = go.Figure([
    go.Bar(name=name, x=x, y=[rate(step, attempt) for step in WALLET_STEPS],
           marker=dict(color=color, line=dict(color="#fff", width=2)),
           text=[label(step, attempt) for step in WALLET_STEPS], textposition="outside", cliponaxis=False,
           customdata=[f"{blocking[step][attempt]['blocked']} sur {blocking[step][attempt]['reached']}"
                       for step in WALLET_STEPS],
           hovertemplate="%{x} · " + name + "<br>%{customdata} sessions en difficulté<extra></extra>")
    for name, attempt, color in [("1er essai, avec Salma", "guided", BLUE), ("2e essai, seul", "alone", ORANGE)]
])
fig.update_layout(
    height=340, template="simple_white", bargap=0.35, bargroupgap=0.08,
    font=dict(family="Atkinson Hyperlegible, sans-serif", size=15, color=MUTED),
    margin=dict(l=10, r=10, t=40, b=10), hoverlabel=dict(font_size=15),
    legend=dict(orientation="h", x=0, y=1.12, title=None),
)
fig.update_yaxes(tickformat=".0%", range=[0, 1.1], gridcolor=GRID, zeroline=False, linecolor=GRID,
                 title="sessions en difficulté")
fig.update_xaxes(linecolor=GRID)
st.plotly_chart(fig, config={"displayModeBar": False})
st.caption(f"En difficulté = erreur, aide, « je suis perdu », question ou 20 s d'hésitation. N = {N} sessions.")

# ================= 3. Why =================
parsed = {}
for row in analyses[analyses.session_id.isin(ids)].itertuples():
    try:
        data = json.loads(row.json)
        if "error" not in data and data.get("source") != "rules":  # only real AI analyses explain "why"
            parsed[row.session_id] = data
    except (TypeError, ValueError):
        pass
reasons = Counter(r.get("reason", "") for a in parsed.values() for r in a.get("struggle_steps", [])
                  if r.get("reason") and (top_step is None or r.get("step") == top_step))
themes = Counter(t for a in parsed.values() for t in a.get("question_themes", []))

st.subheader("Pourquoi")
why = []
for reason, count in reasons.most_common(2):
    why.append(f"**{html.escape(reason)}** — {count} sur {len(parsed)} sessions analysées")
for theme, count in themes.most_common(3):
    quote = next(((a.get("theme_quotes") or {}).get(theme) for a in parsed.values()
                  if (a.get("theme_quotes") or {}).get(theme)), None)
    why.append(f"On demande : **{theme.replace('_', ' ')}** ({count} sessions)"
               + (f" — « {html.escape(quote)} »" if quote else ""))
st.markdown("\n".join(f"- {line}" for line in why) if why else "Pas encore d'analyse IA des sessions.")

# ================= 4. What to do =================
st.subheader("Que faire")
if st.button("🧠 Générer les recommandations", type="primary"):
    summary = {
        "n_sessions": N,
        "pay_alone_after_one_session": alone_ok,
        "autonomous_no_help_no_error": autonomous,
        "abandons": {"count": len(abandons), "steps": {k: int(v) for k, v in abandons.value_counts().items()}},
        "help_needed_per_person_attempt1_vs_attempt2": [round(need_g, 1), round(need_a, 1)],
        "n_sessions_with_both_attempts": n_pairs,
        "sessions_struggling_by_step": {STEP_NAMES[k]: v for k, v in blocking.items()},
        "main_blocking_step_alone": STEP_NAMES.get(top_step),
        "struggle_reasons": dict(reasons.most_common(3)),
        "question_themes": dict(themes.most_common(5)),
    }
    quotes = tu[tu.speaker == "user"].text.str.slice(0, 90).drop_duplicates().head(8).tolist()
    with st.spinner("Analyse des données…"):
        st.session_state.insights = analysis.cross_session_insights(summary, quotes)
if "insights" in st.session_state:
    items, source = st.session_state.insights
    badge = {"low": "🟡 confiance faible", "medium": "🟠 confiance moyenne", "high": "🟢 confiance forte"}
    for item in items[:3]:
        st.markdown(
            f'<div class="card">🛠️ <b>{html.escape(str(item["action"]))}</b><br>'
            f'📊 {html.escape(str(item["evidence"]))}<br>'
            f'<small>{html.escape(str(item["finding"]))} · ✅ {html.escape(str(item["how_to_verify"]))} · '
            f'{badge.get(item["confidence"], item["confidence"])} · n = {html.escape(str(item["n_sessions"]))}</small></div>',
            unsafe_allow_html=True,
        )
    st.caption(f"Source : {'règles simples (aucune IA disponible)' if source == 'rules' else source}")
