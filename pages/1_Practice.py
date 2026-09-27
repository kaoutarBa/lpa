"""Wallet replica: 6 screens, simulated mistakes, mode + variant, event logging."""
import streamlit as st

import db
from content import ERRORS, HELP, PRACTICE as T, STEPS, TEXT, WALLET, darija, inject_css, reassure

st.set_page_config(page_title="Mahfadati Wallet", page_icon="💳", layout="centered")
inject_css()
db.init_db()

if "session_id" not in st.session_state:
    st.title(TEXT["practice_title"])
    st.markdown(TEXT["no_session"])
    if st.button(TEXT["go_home"], type="primary"):
        st.switch_page("app.py")
    st.stop()

ss = st.session_state
sid = ss.session_id
ss.setdefault("step", "mode")
ss.setdefault("variant", "A")
ss.setdefault("error", None)      # step name whose error message to show
ss.setdefault("show_help", False)

ORDER = ["home", "biller", "reference", "confirm", "otp", "receipt"]


def go(step):
    ss.step = step
    ss.error = None
    ss.show_help = False
    db.log_event(sid, step, "step_enter")
    st.rerun()


def money(x):
    return f"{x:,.2f} MAD".replace(",", " ").replace(".", ",")


# ---------- Sidebar: tester-only variant toggle ----------
with st.sidebar:
    st.markdown(f"**{T['sidebar_admin']}**")
    variant = "B" if st.toggle(T["variant_label"], value=ss.variant == "B") else "A"
    if variant != ss.variant:
        ss.variant = variant
        db.update_session(sid, variant=variant)

step = ss.step
st.title(TEXT["practice_title"])
reassure(TEXT["reassure"])

# ---------- Mode choice (before the wallet) ----------
if step == "mode":
    st.subheader(T["mode_title"])
    darija(T["mode_darija"])
    if st.button(T["mode_coached"], type="primary"):
        ss.mode = "coached"
        db.update_session(sid, mode="coached", variant=ss.variant)
        go("home")
    if st.button(T["mode_alone"]):
        ss.mode = "alone"
        db.update_session(sid, mode="alone", variant=ss.variant)
        go("home")
    st.stop()

# ---------- Coach instruction (coached mode only; the AI coach arrives in milestone 3) ----------
if ss.mode == "coached":
    fr, dj = STEPS[step]
    st.markdown(f'<div class="coach">👩‍🏫 {fr}<br><i>🗣️ {dj}</i></div>', unsafe_allow_html=True)
    st.write("")

# ---------- Screens ----------
if step == "home":
    st.markdown(
        f'<div class="card">{T["balance_label"]}<br><span class="balance">{money(WALLET["balance"])}</span></div>',
        unsafe_allow_html=True,
    )
    if st.button(T["pay_bill"], type="primary"):
        go("biller")

elif step == "biller":
    st.subheader(T["biller_title"])
    if st.button(T["biller_electricity"], type="primary"):
        go("reference")
    if st.button(T["biller_water"]):
        st.info(T["water_info"])

elif step == "reference":
    st.subheader(T["reference_title"])
    st.markdown(
        f'<div class="bill"><b>{T["bill_header"]}</b><br><br>'
        f'{T["bill_ref_label"]} : <span class="ref">{WALLET["reference"]}</span><br>'
        f'{T["bill_amount_label"]} : <b>{money(WALLET["amount"])}</b></div>',
        unsafe_allow_html=True,
    )
    st.write("")
    with st.form("reference_form"):
        typed = st.text_input(T["reference_label"], placeholder="EL-....-....")
        if st.form_submit_button(T["next"], type="primary"):
            # Forgiving check: ignore case, spaces and dashes.
            clean = typed.upper().replace(" ", "").replace("-", "")
            if clean == WALLET["reference"].replace("-", ""):
                go("confirm")
            else:
                db.log_event(sid, step, "error_reference", typed[:40])
                ss.error = step

elif step == "confirm":
    st.subheader(T["confirm_title"])
    st.markdown(
        f'<div class="card">'
        f'🏢 {T["confirm_biller"]} : <b>{WALLET["biller"]} — {WALLET["bill_type"]}</b><br>'
        f'🔢 {T["bill_ref_label"]} : <b>{WALLET["reference"]}</b><br>'
        f'💰 {T["bill_amount_label"]} : <b>{money(WALLET["amount"])}</b></div>',
        unsafe_allow_html=True,
    )
    if st.button(T["confirm_button"], type="primary"):
        go("otp")

elif step == "otp":
    st.subheader(T["otp_title"])
    st.markdown(
        f'<div class="sms"><b>{T["sms_from"]}</b><br>{T["sms_text"]}</div>', unsafe_allow_html=True
    )
    with st.form("otp_form"):
        typed = st.text_input(T[f"otp_label_{ss.variant}"], max_chars=6)
        if st.form_submit_button(T["validate"], type="primary"):
            if typed.strip() == WALLET["otp"]:
                db.log_event(sid, step, "complete")
                mistakes = db.count_events(sid, ["error_reference", "error_otp", "help_request", "lost"])
                db.update_session(
                    sid,
                    ended_at=db.now(),
                    completed=1,
                    completed_alone=int(ss.mode == "alone" and mistakes == 0),
                )
                go("receipt")
            else:
                db.log_event(sid, step, "error_otp")
                ss.error = step

elif step == "receipt":
    st.success(T["receipt_title"])
    st.markdown(
        f'<div class="card">'
        f'🏢 {WALLET["biller"]} — {WALLET["bill_type"]}<br>'
        f'🔢 {T["bill_ref_label"]} : <b>{WALLET["reference"]}</b><br>'
        f'💰 {T["bill_amount_label"]} : <b>{money(WALLET["amount"])}</b><br>'
        f'{T["new_balance"]} : <b>{money(WALLET["balance"] - WALLET["amount"])}</b></div>',
        unsafe_allow_html=True,
    )
    st.markdown(f"### {T['receipt_value']}")
    darija(T["receipt_value_darija"])
    if st.button(T["restart"], type="primary"):
        # A new practice run is a new anonymous session.
        ss.session_id = db.create_session(consent=1)
        ss.step = "mode"
        st.rerun()
    st.stop()

# ---------- Friendly error after a mistake ----------
if ss.error == step:
    fr, dj = ERRORS[step]
    st.warning(fr)
    darija(dj)
    st.info(HELP[step])  # replaced by the AI coach's auto-explanation in milestone 3

if ss.show_help:
    st.info(HELP[step])

# ---------- Back / I'm lost / help (every screen) ----------
st.divider()
col_back, col_lost = st.columns(2)
with col_back:
    if st.button(T["back"]):
        db.log_event(sid, step, "back")
        if step == "home":
            st.switch_page("app.py")
        ss.step = ORDER[ORDER.index(step) - 1]
        ss.error = None
        ss.show_help = False
        st.rerun()
with col_lost:
    if st.button(T["lost"]):
        db.log_event(sid, step, "lost")
        ss.show_help = True
        st.rerun()

if ss.mode == "alone" and st.button(T["help"]):
    db.log_event(sid, step, "help_request")
    ss.show_help = True
    st.rerun()
