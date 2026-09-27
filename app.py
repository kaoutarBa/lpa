"""Home: consent screen, optional profile, short lesson."""
import streamlit as st

import db
from content import TEXT, darija, inject_css, reassure

st.set_page_config(page_title="Learn, Practice, Adopt", page_icon="💳", layout="centered")
inject_css()
db.init_db()

if "stage" not in st.session_state:
    st.session_state.stage = "consent"


def go(stage):
    st.session_state.stage = stage
    st.rerun()


stage = st.session_state.stage

if stage == "consent":
    st.title(TEXT["consent_title"])
    reassure(TEXT["reassure"])
    st.markdown(TEXT["consent_body"])
    darija(TEXT["consent_darija"])
    if st.button(TEXT["consent_yes"], type="primary"):
        st.session_state.session_id = db.create_session(consent=1)
        go("profile")
    if st.button(TEXT["consent_no"]):
        go("declined")

elif stage == "declined":
    st.title(TEXT["consent_title"])
    st.markdown(TEXT["consent_declined"])
    if st.button(TEXT["go_home"]):
        go("consent")

elif stage == "profile":
    st.title(TEXT["profile_title"])
    darija(TEXT["profile_darija"])
    age = st.radio(TEXT["age_label"], TEXT["age_options"], index=None)
    edu = st.radio(TEXT["edu_label"], TEXT["edu_options"], index=None)
    if st.button(TEXT["profile_save"], type="primary"):
        db.update_session(st.session_state.session_id, age_range=age, education=edu)
        go("lesson")
    if st.button(TEXT["profile_skip"]):
        go("lesson")

elif stage == "lesson":
    st.title(TEXT["lesson_title"])
    reassure(TEXT["reassure"])
    st.markdown(TEXT["lesson_body"])
    darija(TEXT["lesson_darija"])
    if st.button(TEXT["lesson_start"], type="primary"):
        st.switch_page("pages/1_Practice.py")
