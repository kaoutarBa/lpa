"""Speech in and out.

- Text-to-speech: gTTS sends the text to Google's public TTS service and gets back an MP3.
  Salma's fixed lines (content.py) are generated once, in a background thread at startup, and saved
  in audio_cache/ so the call stays fast. AI answers are generated on the fly (not saved).
- Speech-to-text: Whisper, hosted by Groq, turns the recorded voice into text. We pass
  language="fr" so it does not have to guess. The recording stays in memory and is never saved.
If a service is unreachable, these functions return None and the app continues with text only.
"""
import hashlib
import io
import os
import threading
import time

import streamlit as st
from gtts import gTTS
from openai import OpenAI

from coach import secret
from content import LANG, T

CACHE_DIR = "audio_cache"
_tts_down_until = 0.0  # after a failure (e.g. offline), skip gTTS for a minute so pages stay fast


def _path(text):
    return os.path.join(CACHE_DIR, hashlib.md5(f"{LANG}:{text}".encode()).hexdigest()[:16] + ".mp3")


def tts(text, cache=False):
    """MP3 bytes for `text`, or None if speech is unavailable."""
    global _tts_down_until
    path = _path(text)
    if os.path.exists(path):
        with open(path, "rb") as f:
            return f.read()
    if time.time() < _tts_down_until:
        return None
    try:
        buf = io.BytesIO()
        gTTS(text, lang=LANG, timeout=5).write_to_fp(buf)
        data = buf.getvalue()
    except Exception as e:
        print(f"[voice] gTTS failed: {type(e).__name__}: {e}")
        _tts_down_until = time.time() + 60
        return None
    if cache:
        os.makedirs(CACHE_DIR, exist_ok=True)
        tmp = f"{path}.{threading.get_ident()}.tmp"
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
    return data


def fixed_lines():
    lines = list(T["lines"].values()) + T["fillers"] + [c["say"] for c in T["concepts"].values()]
    for group in ("steps", "mistakes", "cache"):
        lines += [item["say"] for item in T[group].values()]
    return lines


@st.cache_resource
def warm_up():
    """Pre-generate all fixed lines once per server process, in the background."""
    thread = threading.Thread(target=lambda: [tts(line, cache=True) for line in fixed_lines()], daemon=True)
    thread.start()
    return thread


def stt_available():
    return bool(secret("GROQ_API_KEY"))


def transcribe(audio_bytes):
    """Voice → French text with Groq Whisper. Returns None on failure."""
    try:
        client = OpenAI(
            base_url=secret("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
            api_key=secret("GROQ_API_KEY"),
            timeout=15,
            max_retries=0,
        )
        result = client.audio.transcriptions.create(
            model=secret("GROQ_STT_MODEL", "whisper-large-v3-turbo"),
            file=("question.wav", audio_bytes),
            language=LANG,
        )
        return (result.text or "").strip() or None
    except Exception as e:
        print(f"[voice] transcription failed: {type(e).__name__}: {e}")
        return None
