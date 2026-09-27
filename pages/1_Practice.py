"""Practice: a call with Salma (learn → coached → alone → done) on a replica of a mobile wallet."""
import html
import random
import re
import threading
import time

import streamlit as st

import analysis
import coach
import db
import voice
from ear import result_value, salma_ear
from content import T, UI, WALLET, highlight_css, inject_css, reassure

st.set_page_config(page_title="Mahfadati Wallet", page_icon="💳", layout="centered")
inject_css()
db.init_db()
voice.warm_up()  # background pre-generation of Salma's fixed lines (first run only)

ss = st.session_state
if "session_id" not in ss:
    st.title(UI["app_title"])
    st.markdown(UI["no_session"])
    if st.button(UI["go_home"], type="primary"):
        st.switch_page("app.py")
    st.stop()

DEFAULTS = {
    "call": "idle",          # idle | active | ended
    "mode": None,            # learn | coached | alone | done
    "step": "lesson",        # lesson | home | biller | reference | confirm | otp | receipt | done
    "lesson": 0,
    "subs": [],              # captions: [(speaker, text)]
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
    "last_source": "",       # provider + latency of Salma's last line (shown for the demo)
    "to_say": [],            # lines to play on the next render: [(text, is_fixed)]
    "mic_n": 0,              # bumps the mic widget key so each recording is used once
    "analyzed": False,
    "nudged": [],            # screens where Salma already relaunched after 20 s of silence
    "ear_ack": 0,            # bumped each time Python handles something the ear sent
    "alone_nudges": 0,       # idle nudges in the current alone run
}
for key, value in DEFAULTS.items():
    ss.setdefault(key, value.copy() if isinstance(value, (list, dict)) else value)
ss.setdefault("variant", "A")

sid = ss.session_id
WALLET_STEPS = ["home", "biller", "reference", "confirm", "otp", "receipt"]
SLIPS = ["error_reference", "error_otp", "help_request", "lost"]
LOST_WORDS = re.compile(r"\b(perdue?|comprends pas|aide[rz]?)\b", re.IGNORECASE)


# ---------- helpers ----------
def log(type, detail=""):
    db.log_event(sid, ss.mode, ss.step, type, detail)
    if ss.mode == "alone" and type in SLIPS:
        ss.alone_slips += 1


def speak(say, highlight=None, provider="fixed", latency_ms=0, input_type="fixed"):
    """Salma says something: caption, highlight, turn log."""
    ss.subs.append(("salma", say))
    ss.to_say.append((say, provider == "fixed" or provider == "cache"))
    ss.history.append({"role": "assistant", "content": say})
    ss.highlight = highlight
    ss.last_source = provider if provider in ("fixed", "cache") else f"{provider} · {latency_ms} ms"
    db.log_turn(sid, ss.mode, ss.step, "coach", say, input_type, provider, latency_ms, highlight)


def set_mode(mode):
    ss.mode = mode
    with db.connect() as conn:
        reached = conn.execute("SELECT mode_reached FROM sessions WHERE id = ?", (sid,)).fetchone()[0]
    if reached not in db.MODES or db.MODES.index(mode) > db.MODES.index(reached):
        db.update_session(sid, mode_reached=mode)


def go(step):
    ss.step = step
    ss.error = None
    ss.highlight = None
    ss.last_action = ""
    log("step_enter")
    if ss.mode == "coached":
        speak(**T["steps"][step])
    st.rerun()


def answer(message, is_question=False):
    """Salma answers a question or reacts to an event, via the AI coach (with fallbacks)."""
    screen, extra = ss.step, ""
    if ss.mode == "learn":
        lesson = T["lessons"][ss.lesson]
        screen, extra = "lesson", f"Leçon affichée : « {lesson['title']} » — {lesson['say']}"
    think()
    res = coach.ask(
        message, screen, ss.mode, ss.history, ss.last_action,
        ss.errors.get((ss.mode, ss.step), 0), extra, is_question,
    )
    if is_question:
        ss.history.append({"role": "user", "content": message})
    speak(res["say"], res["highlight"], res["provider"], res["latency_ms"], input_type="ai")


def think():
    """Never silent: show "Salma réfléchit…" and play a short pre-generated filler while the AI works."""
    with thinking.container():
        st.markdown(f'<p class="thinking">⏳ {UI["thinking"]}</p>', unsafe_allow_html=True)
        filler = voice.tts(random.choice(T["fillers"]), cache=True)
        if filler:
            st.audio(filler, format="audio/mp3", autoplay=True)


def handle_question(text, input_type):
    """The user talked (voice) or typed a question."""
    ss.subs.append(("you", text))
    db.log_turn(sid, ss.mode, ss.step, "user", text, input_type)
    if ss.mode == "alone":
        log("help_request", input_type)
    ss.last_action = "a posé une question"
    answer(text, is_question=True)
    slip_in_alone()
    st.rerun()


def lost(input_type=None, text=None):
    """« Je suis perdu(e) » — the button, or a spoken phrase with « perdu », « aide », « comprends pas »."""
    if text:
        ss.subs.append(("you", text))
        db.log_turn(sid, ss.mode, ss.step, "user", text, input_type)
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


def screen_key():
    return f"{sid[:8]}:{ss.mode}:{ss.step}:{ss.lesson}"


def slip_in_alone():
    """In alone mode, after 2+ errors or help requests, Salma offers one more coached round."""
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


def money(x):
    return f"{x:,.2f} MAD".replace(",", " ").replace(".", ",")


def reset_call():
    for key in DEFAULTS:
        ss.pop(key, None)


# ---------- sidebar: tester-only variant toggle ----------
with st.sidebar:
    st.markdown(f"**{UI['sidebar_admin']}**")
    variant = "B" if st.toggle(UI["variant_label"], value=ss.variant == "B") else "A"
    if variant != ss.variant:
        ss.variant = variant
        db.update_session(sid, variant=variant)

# ---------- call not started / ended ----------
if ss.call == "idle":
    st.title(UI["call_title"])
    reassure(UI["reassure"])
    st.markdown(UI["call_intro"])
    if st.button(UI["call_button"], type="primary", key="btn_call"):
        ss.call = "active"
        ss.call_started = time.time()
        db.update_session(sid, variant=ss.variant)
        set_mode("learn")
        ss.step = "lesson"
        log("step_enter", "lesson_1")
        speak(T["lines"]["greeting"])
        speak(T["lessons"][0]["say"], "lesson_card")
        st.rerun()
    st.stop()

if ss.call == "ended":
    st.title(UI["call_ended"])
    if st.button(UI["call_again"], type="primary"):
        ss.call = "active"
        speak(T["lines"]["resume"])
        st.rerun()
    if st.button(UI["go_home"]):
        st.switch_page("app.py")
    st.stop()

# ---------- call header: Salma's ear (continuous listening, status, timer) + hang up ----------
last_salma = next((text for who, text in reversed(ss.subs) if who == "salma"), "")
ear = salma_ear(
    listen=ss.mode != "done", nudge=ss.mode != "done", screen=screen_key(),
    turn=f"{len(ss.subs)}-{ss.ear_ack}", elapsed=int(time.time() - ss.call_started), last_line=last_salma,
    labels={k: UI[k] for k in ("listening", "speaking", "thinking", "paused", "nomic")} | {"title": UI["call_header"]},
)
if result_value(ear, "unsupported"):
    ss.speech_supported = False  # no Web Speech API or mic refused: fallback inputs for the rest of the session
speech_supported = ss.get("speech_supported", True)
if st.button(UI["hangup"], key="btn_hangup"):
    log("hangup")
    ss.call = "ended"
    st.rerun()

captions = "".join(
    f'<p class="{"you" if who == "you" else ""}"><b>{UI[who]} :</b> {html.escape(text)}</p>'
    for who, text in ss.subs[-3:]
)
# Salma speaks: play what she said since the last render (fixed lines come from the audio cache).
audio = b""
for text, fixed in ss.to_say:
    audio += voice.tts(text, cache=fixed) or b""
ss.to_say = []
st.markdown(
    f'<div class="callpanel"><div class="subs">{captions}</div></div>',
    unsafe_allow_html=True,
)
if audio:
    st.audio(audio, format="audio/mp3", autoplay=True)
if ss.last_source:
    st.caption(f"🔌 {ss.last_source}")
thinking = st.empty()  # "Salma réfléchit…" while the AI answers
highlight_css(ss.highlight)

reassure(UI["reassure"])
if ss.mode == "alone":
    st.caption(UI["alone_badge"])

step = ss.step

# ---------- Learn: short spoken lessons ----------
if ss.mode == "learn":
    lesson = T["lessons"][ss.lesson]
    st.markdown(
        f'<div class="lesson" id="lesson_card"><h3>{lesson["title"]}</h3><p>{lesson["say"]}</p></div>',
        unsafe_allow_html=True,
    )
    last = ss.lesson == len(T["lessons"]) - 1
    if st.button(UI["start_practice"] if last else UI["next"], type="primary", key="btn_next"):
        if last:
            set_mode("coached")
            go("home")
        ss.lesson += 1
        log("step_enter", f"lesson_{ss.lesson + 1}")
        speak(T["lessons"][ss.lesson]["say"], "lesson_card")
        st.rerun()

# ---------- Wallet screens ----------
elif step == "home":
    st.subheader(UI["app_title"])
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
    with st.form("reference_form"):
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
    with st.form("otp_form"):
        typed = st.text_input(UI[f"otp_label_{ss.variant}"], max_chars=6, key="input_otp")
        if st.form_submit_button(UI["validate"], type="primary"):
            if typed.strip() != WALLET["otp"]:
                mistake("otp", typed)
            log("complete")
            if ss.mode == "coached":
                go("receipt")
            # Alone run finished: this is the "Adopt" moment.
            ss.alone_secs = int(time.time() - (ss.alone_started or time.time()))
            db.update_session(sid, ended_at=db.now(), completed=1, completed_alone=int(ss.alone_slips == 0 and ss.alone_nudges == 0))
            set_mode("done")
            ss.step = "done"
            ss.highlight = None
            log("step_enter")
            speak(T["lines"]["done"])
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
    st.title(UI["done_title"])
    mins, secs = divmod(ss.alone_secs or 0, 60)
    st.markdown(
        f'<div class="card" id="receipt">{UI["done_time"]}<br><span class="big-value">{mins} min {secs:02d} s</span>'
        f'<br>🏢 {WALLET["biller"]} — {money(WALLET["amount"])} ✅</div>',
        unsafe_allow_html=True,
    )
    st.markdown(f"### {UI['done_value']}")
    if st.button(UI["restart"], type="primary", key="btn_restart"):
        reset_call()
        ss.session_id = db.create_session(consent=1)
        st.rerun()
    if not ss.analyzed:  # in the background: the analysis can take ~10 s and must not block the screen
        ss.analyzed = True
        threading.Thread(target=analysis.analyze_session, args=(sid,), daemon=True).start()
    st.stop()

# ---------- friendly error ----------
if ss.error:
    st.warning(UI[ss.error])

# ---------- repeat offer (alone, after 2+ slips) ----------
if ss.mode == "alone" and ss.repeat_offered and not ss.repeat_declined:
    st.info(T["lines"]["repeat_offer"])
    if st.button(UI["repeat_yes"], key="btn_repeat"):
        log("repeat_coached")
        set_mode("coached")
        ss.repeat_offered = False
        go("home")
    if st.button(UI["repeat_no"], key="btn_repeat_no"):
        ss.repeat_declined = True
        st.rerun()

# ---------- other ways to talk to Salma (continuous listening is the main one) ----------
def fallback_inputs():
    if voice.stt_available():
        recording = st.audio_input(UI["mic_label"], key=f"mic_{ss.mic_n}")
        if recording:
            ss.mic_n += 1  # fresh widget next time, so this recording is used once
            think()
            heard = voice.transcribe(recording.getvalue())
            del recording  # never stored
            if heard:
                handle_voice(heard[:300])
            speak(UI["not_understood"])
            st.rerun()
    with st.form("ask_form", clear_on_submit=True):
        question = st.text_input(UI["text_label"], key="input_question")
        sent = st.form_submit_button(UI["send"])
    if sent and question.strip():
        handle_question(question.strip()[:300], "text")


def handle_voice(text):
    if LOST_WORDS.search(text):
        lost("voice", text)
    handle_question(text, "voice")


st.divider()
if speech_supported:
    with st.expander(UI["fallback_title"]):
        fallback_inputs()
else:
    fallback_inputs()  # no Web Speech API (or mic refused): show the fallback directly

# ---------- I'm lost / help / back ----------
if st.button(UI["lost"], key="btn_lost"):
    lost()

if ss.mode == "alone" and st.button(UI["help"], key="btn_help"):
    log("help_request")
    ss.last_action = "a appuyé sur « Aide »"
    answer("La personne demande de l'aide sur cet écran.")
    slip_in_alone()
    st.rerun()

if step in WALLET_STEPS[1:-1] and st.button(UI["back"], key="btn_back"):
    log("back")
    ss.step = WALLET_STEPS[WALLET_STEPS.index(step) - 1]
    ss.error = None
    ss.highlight = None
    st.rerun()

# ---------- what the ear heard (handled last, once the screen is drawn) ----------
heard = result_value(ear, "speech")
if heard:
    ss.ear_ack += 1
    handle_voice(str(heard)[:300])
if result_value(ear, "idle"):
    ss.ear_ack += 1
    nudge()
