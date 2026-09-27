"""Dashboard for the wallet product manager: where users struggle, why, and what to fix."""
import html
import json
from collections import Counter

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import analysis
import db
from content import UI, inject_css

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
inject_css()
st.markdown("<style>.block-container { max-width: 1100px; }</style>", unsafe_allow_html=True)
db.init_db()

# Validated categorical slots (light surface) + recessive ink/grid.
BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e6e6e3"
STEPS = {"home": "Accueil", "biller": "Facturier", "reference": "Référence", "confirm": "Confirmation", "otp": "Code SMS"}
HELP_TYPES = ["help_request", "lost"]
ERROR_TYPES = ["error_reference", "error_otp"]
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
    if pd.isna(x):
        return "—"
    m, s = divmod(int(x), 60)
    return f"{m} min {s:02d} s"


def alone_times(ev):
    """Seconds from the start of the last alone run to its completion, per session."""
    out = {}
    ev = ev.assign(t=pd.to_datetime(ev.ts, utc=True)).sort_values("t")
    for sid, g in ev[ev["mode"] == "alone"].groupby("session_id"):
        done = g[g.type == "complete"]
        if done.empty:
            continue
        end = done.t.iloc[-1]
        starts = g[(g.type == "step_enter") & (g.step == "home") & (g.t <= end)]
        if not starts.empty:
            out[sid] = (end - starts.t.iloc[-1]).total_seconds()
    return pd.Series(out, dtype=float)


# ---------- load ----------
with db.connect() as conn:
    sessions = pd.read_sql("SELECT * FROM sessions WHERE consent = 1 AND mode_reached IS NOT NULL", conn)
    events = pd.read_sql("SELECT * FROM events", conn)
    turns = pd.read_sql("SELECT * FROM turns", conn)
    analyses = pd.read_sql("SELECT * FROM analyses", conn)
sessions["variant"] = sessions["variant"].fillna("A")

# ---------- sidebar: filters + dev helper ----------
with st.sidebar:
    st.markdown("**🔎 Filtres**")
    include_sim = st.checkbox("Inclure les sessions simulées", value=False)
    variants = st.multiselect("Variante", ["A", "B"], default=["A", "B"])
    st.divider()
    st.markdown("**🛠️ Dev**")
    if st.button("🧪 Générer 10 sessions simulées"):
        db.generate_simulated_sessions(10)
        st.rerun()
    if st.button("🗑️ Supprimer les simulées"):
        db.delete_simulated_sessions()
        st.rerun()

s = sessions[sessions.variant.isin(variants)]
if not include_sim:
    s = s[s.is_simulated == 0]
ids = set(s.id)
ev = events[events.session_id.isin(ids)]
tu = turns[turns.session_id.isin(ids)]
N = len(s)
n_sim = int(s.is_simulated.sum())

st.title(UI["dashboard_title"])
st.caption(f"N = {N} sessions · {N - n_sim} réelles · {n_sim} simulées · variantes : {', '.join(variants) or '—'}")
if n_sim:
    st.warning(f"⚠️ {n_sim} des {N} sessions affichées sont **SIMULÉES** (données de démonstration, pas de vrais utilisateurs).")
if N == 0:
    st.info("Aucune session pour ces filtres. Faites un essai sur la page Practice, "
            "ou cochez « Inclure les sessions simulées » après en avoir généré (barre latérale).")
    st.stop()

# ---------- 1. KPIs ----------
rank = s.mode_reached.map(db.MODES.index)
times = alone_times(ev)
autonomy = s.completed_alone.mean()
k = st.columns(4)
k[0].metric("Sessions (N)", N)
k[1].metric("Atteignent l'essai seul", f"{(rank >= 2).mean():.0%}")
k[2].metric("Autonomie", f"{autonomy:.0%}", help="Essai seul réussi avec 0 erreur et 0 aide.")
k[3].metric("Temps médian (seul)", fmt_secs(times.median() if len(times) else None), help=f"n = {len(times)} essais seuls réussis")
st.caption(" · ".join(f"{m} : {(rank >= i).mean():.0%}" for i, m in enumerate(db.MODES)) + f"  (N = {N})")

left, right = st.columns(2)

# ---------- 2. Journey funnel ----------
with left:
    labels = ["Learn · leçons", "Practice · guidé", "Adopt · seul", "Terminé"]
    counts = [int((rank >= i).sum()) for i in range(len(db.MODES))]
    fig = go.Figure(go.Funnel(
        y=labels, x=counts, textinfo="value+percent initial", marker=dict(color=BLUE),
        connector=dict(fillcolor="#dbe8f8"), textfont=dict(color="#ffffff", size=16),
        hovertemplate="%{y}<br>%{x} sessions (%{percentInitial:.0%})<extra></extra>",
    ))
    st.plotly_chart(style(fig, f"Parcours Learn → Practice → Adopt · N = {N}"), config=PLOT_CONFIG)

# ---------- 3. Friction by step ----------
with right:
    errors = ev[ev.type.isin(ERROR_TYPES)].groupby("step").size()
    helps = ev[ev.type.isin(HELP_TYPES)].groupby("step").size().add(
        tu[(tu.speaker == "user") & (tu["mode"] != "alone")].groupby("step").size(), fill_value=0)
    x = list(STEPS.values())
    fig = go.Figure([
        go.Bar(name="Erreurs", x=x, y=[int(errors.get(k, 0)) for k in STEPS], marker=dict(color=BLUE),
               text=[int(errors.get(k, 0)) or "" for k in STEPS], textposition="outside",
               hovertemplate="%{x}<br>%{y} erreurs<extra></extra>"),
        go.Bar(name="Aides / questions", x=x, y=[int(helps.get(k, 0)) for k in STEPS], marker=dict(color=ORANGE),
               text=[int(helps.get(k, 0)) or "" for k in STEPS], textposition="outside",
               hovertemplate="%{x}<br>%{y} aides ou questions<extra></extra>"),
    ])
    fig.update_traces(marker_line=dict(color="#ffffff", width=2), cliponaxis=False)
    st.plotly_chart(style(fig, f"Friction par écran · N = {N} sessions"), config=PLOT_CONFIG)

# ---------- 4. Question themes ----------
parsed = {}
for row in analyses[analyses.session_id.isin(ids)].itertuples():
    try:
        data = json.loads(row.json)
        if "error" not in data:
            parsed[row.session_id] = data
    except (TypeError, ValueError):
        pass
theme_counts = Counter(t for a in parsed.values() for t in a.get("question_themes", []))

st.subheader("💬 Thèmes des questions")
if not theme_counts:
    st.caption(f"Pas encore d'analyse IA pour ces sessions (analyses disponibles : {len(parsed)}).")
else:
    st.caption(f"Sessions analysées : n = {len(parsed)} sur N = {N}")
    tcol, qcol = st.columns(2)
    top = theme_counts.most_common(6)
    with tcol:
        fig = go.Figure(go.Bar(
            x=[c for _, c in top][::-1], y=[t.replace("_", " ") for t, _ in top][::-1], orientation="h",
            marker=dict(color=BLUE), text=[c for _, c in top][::-1], textposition="outside", cliponaxis=False,
            hovertemplate="%{y}<br>%{x} sessions<extra></extra>",
        ))
        st.plotly_chart(style(fig, f"Sessions par thème · n = {len(parsed)}", 320), config=PLOT_CONFIG)
    with qcol:
        for theme, count in top:
            quotes = []
            for sid, a in parsed.items():
                q = (a.get("theme_quotes") or {}).get(theme)
                if theme in a.get("question_themes", []) and q and q not in quotes:
                    quotes.append(q)
            if not quotes:  # no quote attached by the analysis: fall back to user questions from those sessions
                sids = [sid for sid, a in parsed.items() if theme in a.get("question_themes", [])]
                extra = tu[(tu.session_id.isin(sids)) & (tu.speaker == "user")].text.str.slice(0, 90)
                quotes += [q for q in extra.drop_duplicates() if q not in quotes]
            st.markdown(f"**{theme.replace('_', ' ')}** ({count})  \n" +
                        "  \n".join(f"« {q} »" for q in quotes[:2]))

# ---------- 5. Before / after at the OTP step ----------
st.subheader("🔑 Avant / après : écran du code SMS (A vs B)")
reached_otp = ev[(ev.step == "otp") & (ev.type == "step_enter")].session_id.unique()
otp_ev = ev[(ev.step == "otp") & ev.type.isin(ERROR_TYPES + HELP_TYPES)].groupby("session_id").size()
otp_q = tu[(tu.step == "otp") & (tu.speaker == "user") & (tu["mode"] != "alone")].groupby("session_id").size()
friction = otp_ev.add(otp_q, fill_value=0)
rows = []  # (variant, n sessions, mean friction per session)
for v in ["A", "B"]:
    vs = s[(s.variant == v) & (s.id.isin(reached_otp))].id
    if len(vs):
        rows.append((v, len(vs), friction.reindex(vs, fill_value=0).mean()))
if rows:
    names = {"A": "A · « Saisissez le code OTP »", "B": "B · texte expliqué"}
    fig = go.Figure(go.Bar(
        x=[f"{names[v]}<br>n = {n}" for v, n, _ in rows], y=[m for *_, m in rows],
        marker=dict(color=[BLUE if v == "A" else ORANGE for v, *_ in rows], line=dict(color="#fff", width=2)),
        text=[f"{m:.2f}" for *_, m in rows], textposition="outside", cliponaxis=False, width=0.45,
        hovertemplate="%{x}<br>%{y:.2f} erreurs + aides par session<extra></extra>",
    ))
    fig.update_yaxes(title="erreurs + aides / session")
    c1, c2 = st.columns([3, 2])
    c1.plotly_chart(style(fig, "Friction au code SMS par session", 340), config=PLOT_CONFIG)
    if len(rows) == 2 and rows[0][2] > 0:
        change = (rows[1][2] - rows[0][2]) / rows[0][2]
        c2.metric("B vs A", f"{change:+.0%}", delta=f"{rows[1][2] - rows[0][2]:+.2f} par session", delta_color="inverse")
        c2.caption(f"n = {rows[0][1]} (A) et {rows[1][1]} (B) sessions ayant atteint le code SMS.")
else:
    st.caption("Aucune session n'a encore atteint l'écran du code SMS.")

# ---------- 6. Business card ----------
st.subheader("💼 Potentiel d'adoption")
st.markdown(
    f'<div class="card"><span class="big-value">{autonomy:.0%}</span> des utilisateurs testés ont pu '
    f"<b>payer seuls</b> leur facture après une séance avec Salma.</div>",
    unsafe_allow_html=True,
)
st.caption(f"Projection à partir de N = {N} sessions de test ({n_sim} simulées). Ce n'est pas une mesure de marché.")

# ---------- 7. AI recommendations ----------
st.subheader("🧠 Recommandations")
st.caption("Chaque recommandation cite un chiffre des données. Confiance « low » sous 10 sessions.")
if st.button("🧠 Générer les recommandations", type="primary"):
    summary = {
        "n_sessions": N,
        "n_simulated": n_sim,
        "reach_pct": {m: round((rank >= i).mean() * 100) for i, m in enumerate(db.MODES)},
        "autonomy_pct": round(autonomy * 100),
        "median_alone_seconds": round(times.median()) if len(times) else None,
        "friction_by_step": {k: {"errors": int(errors.get(k, 0)), "help": int(helps.get(k, 0))} for k in STEPS},
        "otp_friction_per_session": {v: {"n": n, "mean": round(m, 2)} for v, n, m in rows},
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
    st.dataframe(s.drop(columns=["consent"]), hide_index=True)
