"""Wallet replica + coach. Screens come in milestone 2."""
import streamlit as st

import db
from content import TEXT, inject_css, reassure

st.set_page_config(page_title="Mahfadati Wallet", page_icon="💳", layout="centered")
inject_css()
db.init_db()

st.title(TEXT["practice_title"])

if "session_id" not in st.session_state:
    st.markdown(TEXT["no_session"])
    if st.button(TEXT["go_home"], type="primary"):
        st.switch_page("app.py")
    st.stop()

reassure(TEXT["reassure"])
st.info("🚧 Les écrans du portefeuille arrivent au milestone 2.")
