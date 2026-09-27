"""Salma's ear: a two-way Streamlit component (components v2) so the user just talks, like on a call.

How it talks to Python:
- The JavaScript (salma_ear.js) runs in the page. With the "whisper" engine it opens the microphone, detects
  when the person starts and stops talking, records that one phrase and sends it to Python, which transcribes
  it with Groq Whisper (then the recording is dropped; nothing is stored). With the "browser" engine it uses
  the browser's own speech recognition (Chrome/Edge) and sends text instead.
- Python → JS: each rerun we pass `data` (listen on/off, engine, current screen, labels, call duration).
  Streamlit calls the JS again when `data` changes.
- JS → Python: triggers "voice" ({audio: base64, mime}), "speech" (text), "idle" (20 s without action) and
  "unsupported" (mic refused). A trigger reruns the script once and holds its value only during that run.
"""
import pathlib

import streamlit as st

_DIR = pathlib.Path(__file__).parent

CSS = """
.salma-bar { display: flex; gap: 12px; align-items: center; color: #ffffff;
  font-family: 'Atkinson Hyperlegible', sans-serif; min-width: 0; }
.avatar { flex: 0 0 46px; height: 46px; border-radius: 50%; background: #ffd9b3; display: flex;
  align-items: center; justify-content: center; font-size: 28px; }
.avatar.speaking { animation: pulse 1.2s ease-in-out infinite; }
@keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(255,214,0,.85); }
  70% { box-shadow: 0 0 0 12px rgba(255,214,0,0); } 100% { box-shadow: 0 0 0 0 rgba(255,214,0,0); } }
.txt { min-width: 0; flex: 1; line-height: 1.25; }
.title { font-size: 16px; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.status { font-size: 16px; font-weight: 700; color: #ffd600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
"""

_JS = (_DIR / "salma_ear.js").read_text(encoding="utf-8")


def salma_ear(listen, nudge, screen, turn, elapsed, labels, engine="whisper", idle_secs=20):
    """Mount the call bar / listener. Returns the component result
    (.voice, .speech, .idle and .unsupported hold a value only during the run they triggered)."""
    # Registered on every run (cheap): keeps working if the Streamlit runtime is recreated.
    component = st.components.v2.component("salma_ear", css=CSS, js=_JS)
    return component(
        key="salma_ear",
        data={
            "listen": listen, "nudge": nudge, "screen": screen, "turn": turn, "elapsed": elapsed,
            "labels": labels, "engine": engine, "idle_secs": idle_secs,
        },
        on_voice_change=lambda: None,
        on_speech_change=lambda: None,
        on_idle_change=lambda: None,
        on_unsupported_change=lambda: None,
    )


def result_value(result, name):
    try:
        return result.get(name)
    except Exception:
        return getattr(result, name, None)
