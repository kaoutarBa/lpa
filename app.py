"""Entry point: page navigation defined in code, with a user view and a PIN-protected provider view.

User view (default): only the journey pages. The dashboard is not in the menu and not reachable by URL.
Provider view: adds the dashboard (with the simulated-sessions tool). Switch at the bottom of the sidebar.
"""
import streamlit as st

import db
from coach import secret

st.set_page_config(page_title="Mahfadati Wallet", page_icon="💳", layout="centered",
                   initial_sidebar_state="collapsed")
db.init_db()
ss = st.session_state
ss.setdefault("provider_view", False)

pages = [
    st.Page("home.py", title="Accueil", icon="🏠", default=True),
    st.Page("pages/1_Practice.py", title="Entraînement", icon="💳", url_path="practice"),
]
if ss.provider_view:
    pages.append(st.Page("pages/2_Dashboard.py", title="Tableau de bord", icon="📊", url_path="dashboard"))
page = st.navigation(pages)

# Discreet view switch, pushed to the bottom of the sidebar.
st.markdown("<style>.st-key-view_switch { order: 99; margin-top: 2rem; opacity: .75; font-size: 16px; }"
            ".st-key-view_switch p, .st-key-view_switch label { font-size: 16px !important; }</style>",
            unsafe_allow_html=True)
with st.sidebar.container(key="view_switch"):
    view = st.radio("Vue", ["Utilisateur", "Fournisseur"], index=int(ss.provider_view), horizontal=True,
                    key="view_choice")
    if view == "Fournisseur" and not ss.provider_view:
        pin = st.text_input("Code PIN", type="password", key="pin_input")
        if pin:
            expected = str(secret("PROVIDER_PIN"))
            if not expected:
                st.caption("PROVIDER_PIN n'est pas défini dans les secrets.")
            elif pin == expected:
                ss.provider_view = True
                st.rerun()
            else:
                st.caption("Code incorrect.")
    elif view == "Utilisateur" and ss.provider_view:
        ss.provider_view = False
        st.rerun()

page.run()
