"""Salma's ear: a two-way Streamlit component (components v2) for continuous speech recognition.

How it talks to Python:
- The JavaScript (salma_ear.js) runs directly in the page. It uses the browser's Web Speech API
  (fr-FR, continuous). In Chrome the audio goes to Google's recognizer; we never receive or store audio,
  only the final text.
- Python → JS: each rerun we pass `data` (listen on/off, current screen, labels, Salma's last line, call
  duration). Streamlit calls the JS again when `data` changes.
- JS → Python: `setTriggerValue("speech", text)` when a phrase ends (~1 s of silence) and
  `setTriggerValue("idle", screen)` after 20 s without action. A trigger reruns the script once, and
  `result.speech` / `result.idle` hold the value only during that run (no need to de-duplicate).
  `setTriggerValue("unsupported", True)` (no Web Speech API, or mic refused): Python remembers it for the
  session and shows the fallback inputs instead.
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
.line { font-size: 15px; opacity: .92; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
"""

_JS = (_DIR / "salma_ear.js").read_text(encoding="utf-8")


def salma_ear(listen, nudge, screen, turn, elapsed, last_line, labels, idle_secs=20):
    """Mount the call bar / speech listener. Returns the component result
    (.speech, .idle and .unsupported hold a value only during the run they triggered)."""
    # Registered on every run (cheap): keeps working if the Streamlit runtime is recreated.
    component = st.components.v2.component("salma_ear", css=CSS, js=_JS)
    return component(
        key="salma_ear",
        data={
            "listen": listen, "nudge": nudge, "screen": screen, "turn": turn, "elapsed": elapsed,
            "last_line": last_line, "labels": labels, "idle_secs": idle_secs,
        },
        on_speech_change=lambda: None,
        on_idle_change=lambda: None,
        on_unsupported_change=lambda: None,
    )


def result_value(result, name):
    try:
        return result.get(name)
    except Exception:
        return getattr(result, name, None)
