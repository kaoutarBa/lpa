"""Home page: consent screen and optional profile. The lessons happen inside the call with Salma."""
import streamlit as st

import db
from content import UI, inject_css, reassure

inject_css()

if "stage" not in st.session_state:
    st.session_state.stage = "consent"


def go(stage):
    st.session_state.stage = stage
    st.rerun()


stage = st.session_state.stage

if stage == "consent":
    st.title(UI["consent_title"])
    reassure(UI["reassure"])
    st.markdown(UI["consent_body"])
    if st.button(UI["consent_yes"], type="primary"):
        st.session_state.session_id = db.create_session(consent=1)
        go("profile")
    if st.button(UI["consent_no"]):
        go("declined")

elif stage == "declined":
    st.title(UI["consent_title"])
    st.markdown(UI["consent_declined"])
    if st.button(UI["go_home"]):
        go("consent")

elif stage == "profile":
    st.title(UI["profile_title"])
    age = st.radio(UI["age_label"], UI["age_options"], index=None)
    edu = st.radio(UI["edu_label"], UI["edu_options"], index=None)
    if st.button(UI["profile_save"], type="primary"):
        db.update_session(st.session_state.session_id, age_range=age, education=edu)
        st.switch_page("pages/1_Practice.py")
    if st.button(UI["profile_skip"]):
        st.switch_page("pages/1_Practice.py")
