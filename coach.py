"""Salma's brain: screen-share context → LLM → {"say", "highlight"}, with a safe fallback chain.

How the AI part works:
- The LLM cannot see the screen, so we *describe* it in words (the "screen share"): which screen,
  what is visible with element ids, what the user just did, how many mistakes. With that, Salma can
  say "the number is at the top of your bill, next to the date".
- The system prompt sets the persona and hard rules (short, French, no invented facts, never ask for
  codes). We also pass only the validated facts for the current screen from content.py, so the model
  answers from our content instead of its general knowledge (this limits hallucinations).
- We ask for JSON {"say": "...", "highlight": "<element id or null>"}: "say" is spoken, "highlight"
  lets the UI draw a yellow outline around an element, like a finger pointing on a shared screen.
- Providers are all OpenAI-compatible, so one `openai` client works for all of them; we only change
  base_url, key and model. They are tried in order with an 8-second timeout each:
  Brev (if set) → NVIDIA Build → Groq → pre-written cached answer. Missing keys are skipped.
"""
import json
import re
import time

import streamlit as st
from openai import OpenAI

from content import T

TIMEOUT = 8

SYSTEM_PROMPT = """You are Salma, a warm and patient guide on a phone call with an older person who is \
learning to pay a bill in a PRACTICE mobile wallet ("Mahfadati Wallet", fake money). You see their \
screen through the screen-share description below.

Rules:
- Answer in {language}, always with "vous". At most 2 short sentences, spoken style: no lists, no markdown, no emoji.
- One idea at a time, everyday words and analogies (the SMS code is "une clé envoyée seulement à vous").
- Never rush, never blame. Praise small successes. You may check understanding ("C'est clair pour vous ?").
- Use ONLY the validated facts and the screen description below. Never invent fees, steps, or features.
- Never ask for real codes, passwords or personal data. Never claim to do an action for the user: tell them what to tap.
- If you are unsure or the question is off-topic, say so kindly and suggest the wallet's official customer support.
- You may point at ONE element on the screen with its id, chosen from: {ids}. Otherwise use null.

Return JSON only, nothing else: {{"say": "...", "highlight": "<id or null>"}}

Validated facts for this screen:
{facts}

Screen share (what the user sees right now):
{screen}"""

MODE_LABELS = {
    "learn": "leçons (la personne écoute des explications)",
    "coached": "entraînement guidé (vous guidez chaque écran)",
    "alone": "essai seul (vous restez silencieuse; la personne vient de vous demander de l'aide)",
    "done": "terminé",
}


def secret(name, default=""):
    try:
        return st.secrets.get(name, default) or default
    except Exception:  # no secrets.toml at all
        return default


def providers():
    """(name, base_url, api_key, model) for every configured chat provider, in fallback order."""
    brev_url = secret("BREV_URL").rstrip("/")
    if brev_url and not brev_url.endswith("/v1"):
        brev_url += "/v1"  # vLLM serves the OpenAI API under /v1
    candidates = [
        ("brev", brev_url, secret("BREV_API_KEY", "EMPTY"), secret("BREV_MODEL")),
        ("build", secret("BUILD_BASE_URL", "https://integrate.api.nvidia.com/v1"),
         secret("NVIDIA_API_KEY"), secret("BUILD_MODEL")),
        ("groq", secret("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
         secret("GROQ_API_KEY"), secret("GROQ_CHAT_MODEL")),
    ]
    return [c for c in candidates if all(c[1:])]


def chat(messages, max_tokens=160, temperature=0.3, timeout=TIMEOUT):
    """Try each provider in order. Returns (text, provider, latency_ms), or (None, None, 0) if all fail."""
    for name, base_url, api_key, model in providers():
        start = time.time()
        try:
            client = OpenAI(base_url=base_url, api_key=api_key, timeout=timeout, max_retries=0)
            resp = client.chat.completions.create(
                model=model, messages=messages, max_tokens=max_tokens, temperature=temperature
            )
            text = (resp.choices[0].message.content or "").strip()
            if text:
                return text, name, int((time.time() - start) * 1000)
        except Exception as e:  # timeout, bad key, network… → next provider
            print(f"[coach] {name} failed: {type(e).__name__}: {e}")
    return None, None, 0


def parse_json(text):
    """Extract the first JSON object/array from an LLM reply (tolerates ```json fences and chatter)."""
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    match = re.search(r"[\[{].*[\]}]", text, flags=re.DOTALL)
    return json.loads(match.group(0) if match else text)


def screen_share(screen, mode, last_action="", errors=0, extra=""):
    info = T["screens"][screen]
    lines = [
        f"- Mode: {MODE_LABELS.get(mode, mode)}",
        f"- Écran: {screen}",
        f"- Visible: {info['visible']} {extra}".strip(),
        f"- La personne vient de: {last_action or 'arriver sur cet écran'}",
        f"- Erreurs sur cet écran: {errors}",
    ]
    return "\n".join(lines)


def ask(message, screen, mode, history, last_action="", errors=0, extra="", is_question=True):
    """Ask Salma. `message` is the user's question, or a description of what just happened.
    Returns {"say", "highlight", "provider", "latency_ms"}."""
    info = T["screens"][screen]
    system = SYSTEM_PROMPT.format(
        language=T["language_name"],
        ids=", ".join(info["ids"]) or "aucun",
        facts=info["facts"],
        screen=screen_share(screen, mode, last_action, errors, extra),
    )
    if not is_question:
        message = f"(Ce n'est pas une question, c'est ce qui vient de se passer : {message} Réagissez calmement.)"
    messages = [{"role": "system", "content": system}, *history[-4:], {"role": "user", "content": message}]

    text, provider, latency = chat(messages)
    if text:
        try:
            data = parse_json(text)
            say, highlight = str(data.get("say", "")).strip(), data.get("highlight")
        except Exception:
            say, highlight = re.sub(r"[*#_`]", "", text).strip(), None  # raw text, no highlight
        if say:
            return {
                "say": say[:400],
                "highlight": highlight if highlight in info["ids"] else None,
                "provider": provider,
                "latency_ms": latency,
            }
    cached = T["cache"][screen]
    return {"say": cached["say"], "highlight": cached["highlight"], "provider": "cache", "latency_ms": 0}
