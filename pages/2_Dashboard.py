"""Dashboard for the wallet product manager. Built in milestone 4."""
import streamlit as st

import db
from content import UI, inject_css

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
inject_css()
db.init_db()

st.title(UI["dashboard_title"])

with db.connect() as conn:
    n_sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
st.metric("Sessions (N)", n_sessions)
st.info("🚧 Graphiques et indicateurs au milestone 4.")
