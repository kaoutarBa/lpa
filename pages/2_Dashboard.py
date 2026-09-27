"""Dashboard for the wallet provider: how people progress, where they struggle, why, and what to fix."""
import html
import json
from collections import Counter

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import analysis
import db
from content import UI, inject_css
from progress import ERROR_TYPES, HELP_TYPES, LEVEL_HELP, LEVELS, STEP_NAMES, sessions_progress, share

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
inject_css()
st.markdown("<style>.block-container { max-width: 1100px; }</style>", unsafe_allow_html=True)
db.init_db()

# Validated categorical slots (light surface) + recessive ink/grid. Aqua is below 3:1 → bars carry labels.
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e6e6e3"
WALLET_STEPS = ["home", "biller", "reference", "confirm", "otp"]
PLOT_CONFIG = {"displayModeBar": False}


def style(fig, title, height=360):
    fig.update_layout(
        title=dict(text=title, font=dict(size=18, color=INK), x=0, y=0.97),
        height=height, template="simple_white", bargap=0.35, bargroupgap=0.08,
        font=dict(family="Atkinson Hyperlegible, sans-serif", size=15, color=MUTED),
        margin=dict(l=10, r=10, t=90, b=10), hoverlabel=dict(font_size=15),
        legend=dict(orientation="h", x=0, y=1.08, yanchor="bottom", title=None),
    )
    fig.update_yaxes(gridcolor=GRID, showgrid=True, zeroline=False, linecolor=GRID)
    fig.update_xaxes(linecolor=GRID)
    return fig


def fmt_secs(x):
    if x is None or pd.isna(x):
        return "—"
    m, s = divmod(int(x), 60)
    return f"{m} min {s:02d} s"


def num(x):
    return f"{x:.1f}".replace(".", ",")


# ---------- load ----------
with db.connect() as conn:
    sessions = pd.read_sql("SELECT * FROM sessions WHERE consent = 1 AND mode_reached IS NOT NULL", conn)
    events = pd.read_sql("SELECT * FROM events", conn)
    turns = pd.read_sql("SELECT * FROM turns", conn)
    analyses = pd.read_sql("SELECT * FROM analyses", conn)

# ---------- sidebar: filter + dev helper ----------
with st.sidebar:
    st.markdown("**🔎 Filtre**")
    include_sim = st.checkbox("Inclure les sessions simulées", value=False)
    st.divider()
    st.markdown("**🛠️ Dev**")
    if st.button("🧪 Generate 10 simulated sessions"):
        db.generate_simulated_sessions(10)
        st.rerun()
    if st.button("🗑️ Supprimer les simulées"):
        db.delete_simulated_sessions()
        st.rerun()

s = sessions if include_sim else sessions[sessions.is_simulated == 0]
ids = set(s.id)
ev = events[events.session_id.isin(ids)]
tu = turns[turns.session_id.isin(ids)]
N = len(s)
n_sim = int(s.is_simulated.sum())

st.title(UI["dashboard_title"])
st.caption(f"N = {N} sessions · {N - n_sim} réelles · {n_sim} simulées")
if n_sim:
    st.warning(f"⚠️ {n_sim} des {N} sessions affichées sont **SIMULÉES** (données de démonstration, pas de vrais utilisateurs).")
if N < 3:
    st.info(f"Pas encore assez de données (N = {N}). Il faut au moins 3 sessions. Faites des essais sur la page "
            "Practice, ou générez des sessions simulées (barre latérale) et cochez « Inclure les sessions simulées ».")
    st.stop()

prog = sessions_progress(s, ev, tu)
levels = prog.level.value_counts().to_dict()
paid = int((prog.level >= 1).sum())
alone_or_almost = int((prog.level >= 3).sum())
pairs = prog[prog.both_done]
n_pairs = len(pairs)
mean = lambda col: float(pairs[col].mean()) if n_pairs else 0.0
need_g = mean("g_help") + mean("g_nudges")  # "help needed" = help requests + Salma's relaunches
need_a = mean("a_help") + mean("a_nudges")

# ================= 1. Summary =================
st.header("1 · Résumé")
k = st.columns(4)
k[0].metric("Sessions (N)", N)
k[1].metric("Ont réussi à payer", share(paid, N))
k[2].metric("Seuls ou presque seuls", share(alone_or_almost, N), help="Niveaux 3 et 4")
k[3].metric("Temps médian (2e essai, seul)", fmt_secs(prog.a_secs.median() if prog.a_secs.notna().any() else None),
            help=f"n = {int(prog.a_secs.notna().sum())} essais seuls réussis")

if n_pairs >= 3 and need_g > 0:
    drop = (need_g - need_a) / need_g
    change = f"de {drop:.0%}" if n_pairs >= 10 else f"de {num(need_g)} à {num(need_a)} par personne"
    change_sentence = f" Entre les deux essais, l'aide nécessaire baisse {change}." if need_a < need_g else \
        " L'aide nécessaire reste stable entre les deux essais."
else:
    change_sentence = ""
st.markdown(
    f'<div class="card"><b>{paid} sur {N}</b> ont réussi à payer, dont <b>{alone_or_almost}</b> presque seuls ou '
    f"seuls.{change_sentence}</div>",
    unsafe_allow_html=True,
)
st.caption(f"Projection sur des sessions de test (N = {N}, dont {n_sim} simulées). Ce n'est pas une mesure de marché.")

left, right = st.columns([3, 2])
with left:
    order = [4, 3, 2, 1, 0]
    counts = [int(levels.get(lv, 0)) for lv in order]
    fig = go.Figure(go.Bar(
        x=counts[::-1], y=[LEVELS[lv] for lv in order][::-1], orientation="h", marker=dict(color=BLUE),
        text=[share(c, N) if c else "" for c in counts][::-1], textposition="outside", cliponaxis=False,
        customdata=[LEVEL_HELP[lv] for lv in order][::-1],
        hovertemplate="%{y}<br>%{x} sessions<br>%{customdata}<extra></extra>",
    ))
    fig.update_xaxes(range=[0, max(counts) * 1.25 + 0.5])  # room for the labels
    st.plotly_chart(style(fig, f"Niveau d'autonomie · N = {N}", 330), config=PLOT_CONFIG)
with right:
    st.markdown("**Les niveaux**")
    st.markdown("  \n".join(f"**{LEVELS[lv]}** : {LEVEL_HELP[lv]}" for lv in order))
    abandons = prog.abandon_step.dropna().map(lambda x: STEP_NAMES.get(x, x)).value_counts()
    if len(abandons):
        st.caption("Abandons : " + " · ".join(f"{step} ({c})" for step, c in abandons.items()))

# ================= 2. Progression between the two attempts =================
st.header("2 · Progression entre les essais")
if n_pairs < 3:
    st.info(f"Pas encore assez de données : {n_pairs} session(s) avec les deux essais terminés (il en faut 3).")
else:
    st.caption(f"1er essai = guidé par Salma · 2e essai = seul · moyennes par personne · n = {n_pairs} sessions "
               "ayant terminé les deux essais")
    m = st.columns(4)
    for col, (label, key) in zip(m, [("Aides", "help"), ("Erreurs", "errors"), ("Relances de Salma", "nudges")]):
        g, a = mean(f"g_{key}"), mean(f"a_{key}")
        col.metric(f"{label} (seul)", num(a), delta=f"{num(a - g)} vs guidé", delta_color="inverse")
    g_t, a_t = pairs.g_secs.median(), pairs.a_secs.median()
    m[3].metric("Temps médian (seul)", fmt_secs(a_t), delta=f"{int(a_t - g_t):+d} s vs guidé", delta_color="inverse")
    cats = ["Aides", "Erreurs", "Relances"]
    fig = go.Figure([
        go.Bar(name="1er essai (guidé)", x=cats, y=[mean("g_help"), mean("g_errors"), mean("g_nudges")],
               marker=dict(color=BLUE, line=dict(color="#fff", width=2)),
               text=[num(mean(c)) for c in ("g_help", "g_errors", "g_nudges")], textposition="outside",
               cliponaxis=False, hovertemplate="%{x} · 1er essai<br>%{y:.1f} par personne<extra></extra>"),
        go.Bar(name="2e essai (seul)", x=cats, y=[mean("a_help"), mean("a_errors"), mean("a_nudges")],
               marker=dict(color=ORANGE, line=dict(color="#fff", width=2)),
               text=[num(mean(c)) for c in ("a_help", "a_errors", "a_nudges")], textposition="outside",
               cliponaxis=False, hovertemplate="%{x} · 2e essai<br>%{y:.1f} par personne<extra></extra>"),
    ])
    fig.update_yaxes(title="par personne")
    st.plotly_chart(style(fig, f"Avant / après : 1er essai guidé vs 2e essai seul · n = {n_pairs}", 340),
                    config=PLOT_CONFIG)

# ================= 3. Difficult steps and why =================
st.header("3 · Étapes difficiles, et pourquoi")
errors = ev[ev.type.isin(ERROR_TYPES)].groupby("step").size()
helps = ev[ev.type.isin(HELP_TYPES)].groupby("step").size().add(
    tu[(tu.speaker == "user") & (tu["mode"] != "alone")].groupby("step").size(), fill_value=0)
nudges = ev[ev.type == "idle_nudge"].groupby("step").size()
friction = {k: {"errors": int(errors.get(k, 0)), "help": int(helps.get(k, 0)), "nudges": int(nudges.get(k, 0))}
            for k in WALLET_STEPS}
x = [STEP_NAMES[k] for k in WALLET_STEPS]
fig = go.Figure([
    go.Bar(name=name, x=x, y=[friction[k][key] for k in WALLET_STEPS], marker=dict(color=color, line=dict(color="#fff", width=2)),
           text=[friction[k][key] or "" for k in WALLET_STEPS], textposition="outside", cliponaxis=False,
           hovertemplate="%{x}<br>%{y} " + unit + "<extra></extra>")
    for name, key, color, unit in [("Erreurs", "errors", BLUE, "erreurs"), ("Aides / questions", "help", ORANGE, "aides"),
                                   ("Relances (hésitation 20 s)", "nudges", AQUA, "relances")]
])
st.plotly_chart(style(fig, f"Difficultés par écran (tous essais) · N = {N} sessions"), config=PLOT_CONFIG)

parsed = {}
for row in analyses[analyses.session_id.isin(ids)].itertuples():
    try:
        data = json.loads(row.json)
        if "error" not in data:
            parsed[row.session_id] = data
    except (TypeError, ValueError):
        pass
top_steps = sorted(WALLET_STEPS, key=lambda k: -sum(friction[k].values()))[:2]
why_cols = st.columns(2)
for col, step in zip(why_cols, top_steps):
    f = friction[step]
    reasons = Counter(r.get("reason", "") for a in parsed.values() for r in a.get("struggle_steps", [])
                      if r.get("step") == step and r.get("reason"))
    with col:
        st.markdown(f"**{STEP_NAMES[step]}** — {f['errors']} erreurs, {f['help']} aides, {f['nudges']} relances")
        if reasons:
            st.markdown("  \n".join(f"• {html.escape(r)} ({c} sessions)" for r, c in reasons.most_common(2)))
        else:
            st.caption("Pas encore d'analyse IA pour expliquer cette étape.")

theme_counts = Counter(t for a in parsed.values() for t in a.get("question_themes", []))
if theme_counts:
    st.markdown(f"**Ce que les gens demandent** (analyses IA : n = {len(parsed)} sur N = {N})")
    tcols = st.columns(3)
    for i, (theme, count) in enumerate(theme_counts.most_common(6)):
        quotes = []
        for a in parsed.values():
            q = (a.get("theme_quotes") or {}).get(theme)
            if theme in a.get("question_themes", []) and q and q not in quotes:
                quotes.append(q)
        if not quotes:  # no quote attached by the analysis: fall back to user questions from those sessions
            sids = [sid for sid, a in parsed.items() if theme in a.get("question_themes", [])]
            quotes = tu[tu.session_id.isin(sids) & (tu.speaker == "user")].text.str.slice(0, 90).drop_duplicates().tolist()
        tcols[i % 3].markdown(f"**{theme.replace('_', ' ')}** ({share(count, len(parsed))})  \n" +
                              "  \n".join(f"« {html.escape(q)} »" for q in quotes[:2]))

# ================= 4. Recommendations =================
st.header("4 · Recommandations")
st.caption("Chaque recommandation cite un chiffre des données. Confiance « low » sous 10 sessions.")
if st.button("🧠 Générer les recommandations", type="primary"):
    summary = {
        "n_sessions": N,
        "n_simulated": n_sim,
        "autonomy_levels": {LEVELS[lv]: int(levels.get(lv, 0)) for lv in LEVELS},
        "paid": paid,
        "alone_or_almost_alone": alone_or_almost,
        "abandon_steps": {k: int(v) for k, v in prog.abandon_step.dropna().value_counts().items()},
        "progression_attempt1_guided_vs_attempt2_alone": {
            "n_sessions_with_both_attempts": n_pairs,
            "help_per_person": [round(mean("g_help"), 1), round(mean("a_help"), 1)],
            "errors_per_person": [round(mean("g_errors"), 1), round(mean("a_errors"), 1)],
            "idle_nudges_per_person": [round(mean("g_nudges"), 1), round(mean("a_nudges"), 1)],
            "median_seconds": [round(pairs.g_secs.median()) if n_pairs else None,
                               round(pairs.a_secs.median()) if n_pairs else None],
        },
        "difficulty_by_step": friction,
        "question_themes": dict(theme_counts),
    }
    quotes = tu[tu.speaker == "user"].text.str.slice(0, 90).drop_duplicates().head(8).tolist()
    with st.spinner("Analyse des données…"):
        st.session_state.insights = analysis.cross_session_insights(summary, quotes)
if "insights" in st.session_state:
    items, source = st.session_state.insights
    st.caption(f"Source : {'règles simples (aucune IA configurée)' if source == 'rules' else source}")
    badge = {"low": "🟡 faible", "medium": "🟠 moyenne", "high": "🟢 forte"}
    for item in items:
        st.markdown(
            f'<div class="card"><b>{html.escape(str(item["finding"]))}</b><br>'
            f'📊 <b>Preuve :</b> {html.escape(str(item["evidence"]))}<br>'
            f'❓ <b>Pourquoi :</b> {html.escape(str(item["why"]))}<br>'
            f'🛠️ <b>Action :</b> {html.escape(str(item["action"]))}<br>'
            f'✅ <b>Vérifier :</b> {html.escape(str(item["how_to_verify"]))}<br>'
            f'<small>Confiance : {badge.get(item["confidence"], item["confidence"])} · '
            f'n = {html.escape(str(item["n_sessions"]))} sessions</small></div>',
            unsafe_allow_html=True,
        )

with st.expander("📋 Voir les données (tableau)"):
    st.dataframe(prog.assign(level=prog.level.map(LEVELS)), hide_index=True)
