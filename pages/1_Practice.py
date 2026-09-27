"""The whole user journey, inside one call with Salma:
consent → optional profile → assisted practice (a concept is explained, then applied in the app)
→ try alone (Salma stays on the line and watches) → done → a few end-of-call questions → thanks.

The page only shows the fictional payment app. Salma is heard, not read: no transcript on screen.
The user talks (continuous listening in the call bar) or types in the "Écrire à Salma" box at the bottom.
"""
import random
import re
import threading
import time

import streamlit as st

import analysis
import coach
import db
import voice
from content import T, UI, WALLET, highlight_css, inject_css
from ear import result_value, salma_ear

inject_css()
voice.warm_up()  # background pre-generation of Salma's fixed lines (first run only)

ss = st.session_state
DEFAULTS = {
    "session_id": None,      # created only after consent
    "call": "idle",          # idle | active | ended | declined
    "mode": None,            # learn (consent + profile) | coached (assisted) | alone | done
    "step": None,            # consent | profile | concept | home | biller | reference | confirm | otp | receipt | done
    "concept": None,         # concept being explained
    "next_step": None,       # wallet screen where the concept is applied
    "concepts_done": [],
    "name": "",              # first name: used by Salma during the call, never stored
    "subs": [],              # conversation (only used for the AI context, never displayed)
    "history": [],           # chat history sent to the LLM
    "highlight": None,       # element id Salma points at
    "error": None,           # error message key to show
    "errors": {},            # (mode, step) -> number of mistakes
    "last_action": "",       # what the user just did (for the screen share)
    "repeat_offered": False,
    "repeat_declined": False,
    "call_started": None,
    "alone_started": None,
    "alone_secs": None,
    "alone_slips": 0,        # errors + help + lost in the current alone run
    "alone_nudges": 0,       # idle nudges in the current alone run
    "to_say": [],            # lines to play on the next render: [(text, is_fixed)]
    "analyzed": False,
    "nudged": [],            # screens where Salma already relaunched after 20 s of silence
    "ear_ack": 0,            # bumped each time Python handles something the ear sent
    "survey_i": 0,           # current end-of-call question
}
for key, value in DEFAULTS.items():
    ss.setdefault(key, value.copy() if isinstance(value, (list, dict)) else value)

WALLET_STEPS = ["home", "biller", "reference", "confirm", "otp", "receipt"]
CONCEPT_BEFORE = {c["before"]: name for name, c in T["concepts"].items()}
SLIPS = ["error_reference", "error_otp", "help_request", "lost"]
LOST_WORDS = re.compile(r"\b(perdue?|comprends pas|aide[rz]?)\b", re.IGNORECASE)
YES_WORDS = re.compile(r"\b(oui|ouais|d'accord|ok|okay|j'accepte|compris|on essaie|allons-y|vas-y|c'est bon|c'est clair)\b",
                       re.IGNORECASE)
NO_WORDS = re.compile(r"\b(non|pas d'accord|je refuse)\b", re.IGNORECASE)

# Fixed call bar on top of the content (never scrolls away); content is pushed down below it.
CALLBAR_CSS = """<style>
.st-key-callbar { position: fixed; top: 0; left: 0; right: 0; z-index: 1000001; background: #0b1f44;
  box-shadow: 0 2px 10px rgba(0,0,0,.35); padding: 10px 12px; max-height: 96px;
  display: flex; flex-direction: row; align-items: center; gap: 10px; }
.st-key-callbar .stElementContainer { width: auto !important; margin: 0; }
.st-key-callbar .st-key-salma_ear { flex: 1 1 auto; min-width: 0; }
.st-key-callbar .st-key-btn_hangup { flex: 0 0 auto; }
.st-key-callbar .st-key-btn_hangup button { min-height: 56px; width: 92px !important; padding: 4px 6px; }
.st-key-callbar .st-key-btn_hangup button p { font-size: 14px !important; white-space: normal; line-height: 1.15;
  word-break: keep-all; overflow-wrap: normal; hyphens: none; }
header[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"] { display: none; }
.block-container { padding-top: 104px !important; }
</style>"""


# ---------- helpers ----------
def log(type, detail=""):
    if ss.session_id:  # nothing is recorded before consent
        db.log_event(ss.session_id, ss.mode, ss.step, type, detail)
    if ss.mode == "alone" and type in SLIPS:
        ss.alone_slips += 1


def speak(say, highlight=None, provider="fixed", latency_ms=0, input_type="fixed"):
    """Salma says something: queued for audio, highlight, turn log."""
    ss.subs.append(("salma", say))
    ss.to_say.append((say, provider in ("fixed", "cache")))
    ss.history.append({"role": "assistant", "content": say})
    ss.highlight = highlight
    if ss.session_id:
        db.log_turn(ss.session_id, ss.mode, ss.step, "coach", say, input_type, provider, latency_ms, highlight)


def set_mode(mode):
    ss.mode = mode
    if not ss.session_id:
        return
    with db.connect() as conn:
        reached = conn.execute("SELECT mode_reached FROM sessions WHERE id = ?", (ss.session_id,)).fetchone()[0]
    if reached not in db.MODES or db.MODES.index(mode) > db.MODES.index(reached):
        db.update_session(ss.session_id, mode_reached=mode)


def reset_screen(step):
    ss.step = step
    ss.error = None
    ss.highlight = None
    ss.last_action = ""


def go(step):
    """Next wallet screen. In assisted mode, the concept it needs is explained first."""
    concept = CONCEPT_BEFORE.get(step)
    if ss.mode == "coached" and concept and concept not in ss.concepts_done:
        ss.concepts_done.append(concept)
        reset_screen("concept")
        ss.concept, ss.next_step = concept, step
        log("step_enter", concept)
        speak(T["concepts"][concept]["say"], "btn_understood")
        st.rerun()
    reset_screen(step)
    log("step_enter")
    if ss.mode == "coached":
        speak(**T["steps"][step])
    st.rerun()


def screen_key():
    return f"{ss.call_started}:{ss.mode}:{ss.step}:{ss.concept}:{ss.survey_i}"


def think():
    """Never silent: play a short pre-generated filler (hidden player) while the AI works."""
    filler = voice.tts(random.choice(T["fillers"]), cache=True)
    if filler:
        with thinking.container():
            st.audio(filler, format="audio/mp3", autoplay=True)


def answer(message, is_question=False):
    """Salma answers a question or reacts to an event, via the AI coach (with fallbacks)."""
    screen, extra = ss.step, ""
    if ss.step == "concept":
        c = T["concepts"][ss.concept]
        extra = f"Concept affiché : « {c['title']} » — {c['text']}"
    if ss.name:
        extra += f" La personne s'appelle {ss.name}."
    think()
    res = coach.ask(
        message, screen, ss.mode, ss.history, ss.last_action,
        ss.errors.get((ss.mode, ss.step), 0), extra, is_question,
    )
    if is_question:
        ss.history.append({"role": "user", "content": message})
    speak(res["say"], res["highlight"], res["provider"], res["latency_ms"], input_type="ai")


def user_says(text, input_type):
    ss.subs.append(("you", text))
    if ss.session_id:
        db.log_turn(ss.session_id, ss.mode, ss.step, "user", text, input_type)


def slip_in_alone():
    """In alone mode, after 2+ errors or help requests, Salma offers one more assisted round."""
    if ss.mode == "alone" and not ss.repeat_offered and ss.alone_slips >= 2:
        ss.repeat_offered = True
        speak(T["lines"]["repeat_offer"])


def mistake(kind, typed):
    """Wrong reference or wrong code."""
    log(f"error_{kind}", typed[:40])
    key = (ss.mode, ss.step)
    ss.errors[key] = ss.errors.get(key, 0) + 1
    ss.error = f"error_{kind}"
    ss.last_action = f"a tapé « {typed[:40]} », ce qui est faux"
    if ss.mode == "coached":
        if ss.errors[key] == 1:
            speak(**T["mistakes"][kind])
        else:
            answer(f"La personne s'est encore trompée ({ss.errors[key]} erreurs sur cet écran).")
    slip_in_alone()
    st.rerun()


def lost(input_type=None, text=None):
    """« Je suis perdu(e) » — the button, or a phrase with « perdu », « aide », « comprends pas »."""
    if text:
        user_says(text, input_type)
    log("lost", input_type or "button")
    ss.last_action = f"a dit « {text} »" if text else "a appuyé sur « Je suis perdu(e) »"
    answer("La personne dit qu'elle est perdue sur cet écran.")
    slip_in_alone()
    st.rerun()


def nudge():
    """20 s without action or speech on this screen: Salma relaunches once, with contextual help."""
    screen = screen_key()
    if screen in ss.nudged:
        st.rerun()
    ss.nudged.append(screen)
    log("idle_nudge")
    if ss.mode == "alone":
        ss.alone_nudges += 1
    ss.last_action = "n'a rien fait ni rien dit depuis 20 secondes"
    answer("La personne hésite depuis 20 secondes sans rien faire. Relancez-la gentiment en une phrase "
           "et montrez-lui l'élément utile sur cet écran.")
    st.rerun()


def start_call():
    ss.call = "active"
    ss.call_started = time.time()
    ss.mode = "learn"
    reset_screen("consent")
    speak(T["lines"]["greeting"], "btn_accept")


def accept():
    ss.session_id = db.create_session(consent=1)
    set_mode("learn")
    reset_screen("profile")
    log("step_enter")
    speak(T["lines"]["profile_intro"], "btn_skip")
    st.rerun()


def decline():
    speak(T["lines"]["declined"])
    ss.call = "declined"
    st.rerun()


def start_assisted():
    set_mode("coached")
    go("home")


def understood():
    go(ss.next_step)


def handle_text(text, input_type):
    """Anything the user said (voice) or wrote."""
    text = text.strip()[:300]
    if not text:
        return
    if ss.step == "survey":  # an answer to the current end-of-call question
        user_says(text, input_type)
        option = spoken_answer(text)
        if option:
            record_answer(option)
        speak(T["lines"]["survey_reprompt"])
        st.rerun()
    if ss.step == "done" and YES_WORDS.search(text):
        user_says(text, input_type)
        start_survey()
    if LOST_WORDS.search(text) and ss.step not in ("consent", "profile"):
        lost(input_type, text)
    user_says(text, input_type)
    if ss.step == "consent" and (YES_WORDS.search(text) or NO_WORDS.search(text)):
        accept() if YES_WORDS.search(text) and not NO_WORDS.search(text) else decline()
    if ss.step == "concept" and YES_WORDS.search(text):
        understood()
    if ss.mode == "alone":
        log("help_request", input_type)
    ss.last_action = "a posé une question"
    answer(text, is_question=True)
    slip_in_alone()
    st.rerun()


def start_survey():
    ss.survey_i = 0
    reset_screen("survey")
    log("step_enter")
    speak(T["survey"][0]["say"])
    st.rerun()


def record_answer(answer):
    """Save one end-of-call answer (None = skipped), then ask the next question or say thanks."""
    q = T["survey"][ss.survey_i]
    if answer:
        db.save_feedback(ss.session_id, q["key"], answer)
    ss.survey_i += 1
    if ss.survey_i < len(T["survey"]):
        speak(T["survey"][ss.survey_i]["say"])
    else:
        reset_screen("thanks")
        log("step_enter")
        speak(T["lines"]["thanks"])
    st.rerun()


def spoken_answer(text):
    """Map a spoken answer ("un peu", "non", "le code"…) to one of the options, or None."""
    low = text.lower()
    for option, words in T["survey"][ss.survey_i]["match"]:
        if any(re.search(rf"\b{re.escape(w)}", low) for w in words):
            return option
    return None


def money(x):
    return f"{x:,.2f} MAD".replace(",", " ").replace(".", ",")


def reset_call():
    for key in DEFAULTS:
        ss.pop(key, None)


def app_header():
    badge = UI["alone_badge"] if ss.mode == "alone" else UI["reassure"]
    st.markdown(f'<div class="apphead"><span class="brand">{UI["app_title"]}</span>'
                f'<span class="badge">{badge}</span></div>', unsafe_allow_html=True)


# ---------- before the call ----------
if ss.call in ("idle", "ended", "declined"):
    with st.container(key="app"):
        app_header()
        if ss.call == "idle":
            st.markdown(f"### {UI['call_title']}")
            st.markdown(UI["call_intro"])
            if st.button(UI["call_button"], type="primary", key="btn_call"):
                start_call()
                st.rerun()
        else:
            st.markdown(f"### {UI['call_ended'] if ss.call == 'ended' else UI['declined']}")
            if st.button(UI["call_again"], type="primary", key="btn_call_again"):
                if ss.call == "ended" and ss.mode:
                    ss.call = "active"
                    speak(T["lines"]["resume"])
                else:
                    reset_call()
                    start_call()
                st.rerun()
    # Audio of Salma's last words (e.g. goodbye) still plays after the call.
    audio = b"".join(voice.tts(text, cache=fixed) or b"" for text, fixed in ss.to_say)
    ss.to_say = []
    if audio:
        st.audio(audio, format="audio/mp3", autoplay=True)
    typed = st.chat_input(UI["chat_placeholder"])
    if typed:  # writing to Salma also starts the call
        if ss.call != "active":
            reset_call()
            start_call()
        thinking = st.empty()
        handle_text(typed, "text")
    st.stop()

# ---------- call bar: fixed at the top (avatar, timer, status, hang up) ----------
st.markdown(CALLBAR_CSS, unsafe_allow_html=True)
with st.container(key="callbar"):
    # Salma's ear: continuous listening + status ("Salma vous écoute…" / "parle…" / "réfléchit…")
    ear = salma_ear(
        listen=ss.step != "thanks", nudge=ss.step not in ("done", "thanks"), screen=screen_key(),
        turn=f"{len(ss.subs)}-{ss.ear_ack}", elapsed=int(time.time() - ss.call_started), last_line="",
        labels={k: UI[k] for k in ("listening", "speaking", "thinking", "paused", "nomic")} | {"title": UI["call_header"]},
    )
    if st.button(UI["hangup"], key="btn_hangup"):
        log("hangup")
        ss.call = "ended"
        st.rerun()
if result_value(ear, "unsupported"):
    print(f"[ear] speech recognition unavailable in this browser: {result_value(ear, 'unsupported')}")

# Salma speaks: play what she said since the last render (fixed lines come from the audio cache).
audio = b"".join(voice.tts(text, cache=fixed) or b"" for text, fixed in ss.to_say)
ss.to_say = []
if audio:
    st.audio(audio, format="audio/mp3", autoplay=True)
thinking = st.empty()  # hidden filler audio while the AI answers
highlight_css(ss.highlight)

step = ss.step

# ---------- the fictional payment app ----------
with st.container(key="app"):
    app_header()

    if step == "consent":
        st.subheader(UI["consent_title"])
        st.markdown(UI["consent_body"])
        if st.button(UI["consent_yes"], type="primary", key="btn_accept"):
            accept()
        if st.button(UI["consent_no"], key="btn_decline"):
            decline()

    elif step == "profile":
        st.subheader(UI["profile_title"])
        st.caption(UI["profile_hint"])
        name = st.text_input(UI["name_label"], key="input_name", max_chars=30)
        age = st.pills(UI["age_label"], UI["age_options"], key="pill_age")
        edu = st.pills(UI["edu_label"], UI["edu_options"], key="pill_edu")
        job = st.pills(UI["job_label"], UI["job_options"], key="pill_job")
        if st.button(UI["profile_save"], type="primary", key="btn_profile"):
            ss.name = name.strip()
            db.update_session(ss.session_id, age_range=age, education=edu, occupation=job)
            start_assisted()
        if st.button(UI["profile_skip"], key="btn_skip"):
            start_assisted()

    elif step == "concept":
        c = T["concepts"][ss.concept]
        st.markdown(f'<div class="concept" id="concept_card"><h3>{c["title"]}</h3><p>{c["text"]}</p></div>',
                    unsafe_allow_html=True)
        if st.button(UI["understood"], type="primary", key="btn_understood"):
            understood()

    elif step == "home":
        st.markdown(
            f'<div class="card" id="balance">{UI["balance_label"]}<br>'
            f'<span class="balance">{money(WALLET["balance"])}</span></div>',
            unsafe_allow_html=True,
        )
        if st.button(UI["pay_bill"], type="primary", key="btn_pay"):
            go("biller")

    elif step == "biller":
        st.subheader(UI["biller_title"])
        if st.button(UI["biller_electricity"], type="primary", key="btn_elec"):
            go("reference")
        if st.button(UI["biller_water"], key="btn_water"):
            ss.last_action = "a appuyé sur Eau au lieu d'Électricité"
            st.info(UI["water_info"])

    elif step == "reference":
        st.subheader(UI["reference_title"])
        st.markdown(
            f'<div class="bill" id="bill_card"><b>{UI["bill_header"]}</b>'
            f'<div class="top"><span>{UI["bill_date_label"]} : {WALLET["bill_date"]}</span>'
            f'<span>{UI["bill_ref_label"]} : <span class="ref" id="bill_ref">{WALLET["reference"]}</span></span></div>'
            f'<br>{UI["bill_amount_label"]} : <b>{money(WALLET["amount"])}</b></div>',
            unsafe_allow_html=True,
        )
        with st.form("reference_form", border=False):
            typed = st.text_input(UI["reference_label"], placeholder="EL-....-....", key="input_ref")
            if st.form_submit_button(UI["continue"], type="primary"):
                # Forgiving check: ignore case, spaces and dashes.
                if typed.upper().replace(" ", "").replace("-", "") == WALLET["reference"].replace("-", ""):
                    go("confirm")
                mistake("reference", typed)

    elif step == "confirm":
        st.subheader(UI["confirm_title"])
        st.markdown(
            f'<div class="card" id="summary">'
            f'🏢 {UI["confirm_biller"]} : <b>{WALLET["biller"]} — {WALLET["bill_type"]}</b><br>'
            f'🔢 {UI["bill_ref_label"]} : <b>{WALLET["reference"]}</b><br>'
            f'💰 {UI["bill_amount_label"]} : <b>{money(WALLET["amount"])}</b></div>',
            unsafe_allow_html=True,
        )
        if st.button(UI["confirm_button"], type="primary", key="btn_confirm"):
            go("otp")

    elif step == "otp":
        st.subheader(UI["otp_title"])
        st.markdown(
            f'<div class="sms" id="sms"><b>{UI["sms_from"]}</b><br>{UI["sms_text"]}</div>', unsafe_allow_html=True
        )
        with st.form("otp_form", border=False):
            typed = st.text_input(UI["otp_label"], max_chars=6, key="input_otp")
            if st.form_submit_button(UI["validate"], type="primary"):
                if typed.strip() != WALLET["otp"]:
                    mistake("otp", typed)
                log("complete")
                if ss.mode == "coached":
                    go("receipt")
                # Alone run finished: this is the "Adopt" moment.
                ss.alone_secs = int(time.time() - (ss.alone_started or time.time()))
                db.update_session(ss.session_id, ended_at=db.now(), completed=1,
                                  completed_alone=int(ss.alone_slips == 0 and ss.alone_nudges == 0))
                set_mode("done")
                reset_screen("done")
                log("step_enter")
                done_line = T["lines"]["done"]
                speak(f"Bravo {ss.name} ! {done_line}" if ss.name else done_line,
                      provider="fixed" if not ss.name else "fixed_name")
                st.rerun()

    elif step == "receipt":
        st.success(UI["receipt_title"])
        st.markdown(
            f'<div class="card" id="receipt">'
            f'🏢 {WALLET["biller"]} — {WALLET["bill_type"]}<br>'
            f'🔢 {UI["bill_ref_label"]} : <b>{WALLET["reference"]}</b><br>'
            f'💰 {UI["bill_amount_label"]} : <b>{money(WALLET["amount"])}</b><br>'
            f'{UI["new_balance"]} : <b>{money(WALLET["balance"] - WALLET["amount"])}</b></div>',
            unsafe_allow_html=True,
        )
        if st.button(UI["try_alone"], type="primary", key="btn_alone"):
            set_mode("alone")
            ss.alone_started = time.time()
            ss.alone_slips = 0
            ss.alone_nudges = 0
            ss.repeat_offered = False
            ss.repeat_declined = False
            speak(T["lines"]["alone_intro"])
            go("home")

    elif step == "done":
        st.subheader(UI["done_title"])
        mins, secs = divmod(ss.alone_secs or 0, 60)
        st.markdown(
            f'<div class="card" id="receipt">{UI["done_time"]}<br>'
            f'<span class="big-value">{mins} min {secs:02d} s</span>'
            f'<br>🏢 {WALLET["biller"]} — {money(WALLET["amount"])} ✅</div>',
            unsafe_allow_html=True,
        )
        st.markdown(f"**{UI['done_value']}**")
        if st.button(UI["survey_start"], type="primary", key="btn_survey"):
            start_survey()

    elif step == "survey":
        q = T["survey"][ss.survey_i]
        st.caption(UI["survey_progress"].format(i=ss.survey_i + 1, n=len(T["survey"])))
        st.subheader(q["say"].replace("Première question. ", "").replace("Dernière question. ", ""))
        for j, option in enumerate(q["options"]):
            if st.button(option, key=f"ans_{ss.survey_i}_{j}"):
                record_answer(option)
        if st.button(UI["survey_skip"], key=f"skip_{ss.survey_i}"):
            record_answer(None)

    elif step == "thanks":
        st.subheader(UI["thanks_title"])
        st.markdown(UI["thanks_body"])
        if st.button(UI["restart"], type="primary", key="btn_restart"):
            reset_call()
            st.rerun()

    if ss.error:
        st.error(UI[ss.error])

    # Salma's offer after 2+ slips in the alone run (she says it; here are the two answers).
    if ss.mode == "alone" and ss.repeat_offered and not ss.repeat_declined:
        if st.button(UI["repeat_yes"], type="primary", key="btn_repeat"):
            log("repeat_coached")
            set_mode("coached")
            ss.repeat_offered = False
            go("home")
        if st.button(UI["repeat_no"], key="btn_repeat_no"):
            ss.repeat_declined = True
            st.rerun()

    if step in WALLET_STEPS[1:-1] and st.button(UI["back"], key="btn_back"):
        log("back")
        reset_screen(WALLET_STEPS[WALLET_STEPS.index(step) - 1])
        st.rerun()

if step in WALLET_STEPS[:-1] and st.button(UI["lost"], key="btn_lost"):
    lost()

if step == "done" and not ss.analyzed:  # in the background: can take ~10 s, must not block the screen
    ss.analyzed = True
    threading.Thread(target=analysis.analyze_session, args=(ss.session_id,), daemon=True).start()

# ---------- what the user said or wrote (handled last, once the screen is drawn) ----------
typed = st.chat_input(UI["chat_placeholder"])
if typed:
    handle_text(typed, "text")
heard = result_value(ear, "speech")
if heard:
    ss.ear_ack += 1
    handle_text(str(heard), "voice")
if result_value(ear, "idle"):
    ss.ear_ack += 1
    nudge()
