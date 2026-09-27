"""Entry point: page navigation defined in code, with a user view and a provider view.

User view (default): only the call with Salma, no menu, no dashboard.
Provider view: adds the dashboard to the menu. Switch at the bottom of the sidebar (open to everyone).
"""
import streamlit as st

import db

st.set_page_config(page_title="Mahfadati Wallet", page_icon="💳", layout="centered",
                   initial_sidebar_state="collapsed")
db.init_db()
ss = st.session_state
ss.setdefault("provider_view", False)

pages = [st.Page("pages/1_Practice.py", title="Appel", icon="📞", default=True)]
if ss.provider_view:
    pages.append(st.Page("pages/2_Dashboard.py", title="Tableau de bord", icon="📊", url_path="dashboard"))
page = st.navigation(pages, position="sidebar" if ss.provider_view else "hidden")

# Discreet view switch, pushed to the bottom of the sidebar.
st.markdown("<style>.st-key-view_switch { order: 99; margin-top: 2rem; opacity: .75; font-size: 16px; }"
            ".st-key-view_switch p, .st-key-view_switch label { font-size: 16px !important; }</style>",
            unsafe_allow_html=True)
with st.sidebar.container(key="view_switch"):
    view = st.radio("Vue", ["Utilisateur", "Fournisseur"], index=int(ss.provider_view), horizontal=True,
                    key="view_choice")
    if (view == "Fournisseur") != ss.provider_view:
        ss.provider_view = view == "Fournisseur"
        st.rerun()

page.run()
