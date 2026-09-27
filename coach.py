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
  base_url, key and model. They are tried in the order of COACH_ORDER (default "groq,build"), 8-second
  timeout each, then a pre-written cached answer. Providers with a missing key or model are skipped.
- Every reply is cleaned before we parse, show or speak it: reasoning ("<think>…"), text around the
  JSON, markdown (**bold**) and emoji are removed.
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
    "learn": "début de l'appel (accord, puis questions facultatives)",
    "coached": "mode assisté (vous expliquez un concept, puis la personne l'applique dans l'app)",
    "alone": "essai seul (vous restez silencieuse; la personne vient de vous demander de l'aide)",
    "done": "terminé",
}


def secret(name, default=""):
    try:
        return st.secrets.get(name, default) or default
    except Exception:  # no secrets.toml at all
        return default


def providers(purpose="coach"):
    """(name, base_url, api_key, model, extra_args) for each configured provider, in fallback order.

    Coach order comes from COACH_ORDER (default "groq,build"). For the analysis we use NVIDIA Build first
    with BUILD_ANALYSIS_MODEL (a bigger model; falls back to BUILD_MODEL), then the coach order.
    A provider with an empty key or model is skipped."""
    brev_url = secret("BREV_URL").rstrip("/")
    if brev_url and not brev_url.endswith("/v1"):
        brev_url += "/v1"  # vLLM serves the OpenAI API under /v1
    build_model = secret("BUILD_MODEL")
    if purpose == "analysis":
        build_model = secret("BUILD_ANALYSIS_MODEL") or build_model
    groq_model = secret("GROQ_CHAT_MODEL")
    known = {
        "brev": (brev_url, secret("BREV_API_KEY", "EMPTY"), secret("BREV_MODEL"), {}),
        "build": (secret("BUILD_BASE_URL", "https://integrate.api.nvidia.com/v1"),
                  secret("NVIDIA_API_KEY"), build_model, {}),
        # gpt-oss models "think" before answering; low effort keeps the answer fast for a phone call.
        "groq": (secret("GROQ_BASE_URL", "https://api.groq.com/openai/v1"), secret("GROQ_API_KEY"), groq_model,
                 {"reasoning_effort": "low"} if groq_model.startswith("openai/gpt-oss") else {}),
    }
    order = [p.strip().lower() for p in secret("COACH_ORDER", "groq,build").split(",") if p.strip()]
    if purpose == "analysis":
        order = ["build"] + [p for p in order if p != "build"]
    return [(name, *known[name]) for name in dict.fromkeys(order) if name in known and all(known[name][:3])]


def chat(messages, max_tokens=160, temperature=0.3, timeout=TIMEOUT, purpose="coach"):
    """Try each provider in order. Returns (clean_text, provider, latency_ms), or (None, None, 0) if all fail."""
    for name, base_url, api_key, model, extra in providers(purpose):
        start = time.time()
        try:
            client = OpenAI(base_url=base_url, api_key=api_key, timeout=timeout, max_retries=0)
            resp = client.chat.completions.create(
                model=model, messages=messages, max_tokens=max_tokens, temperature=temperature, **extra
            )
            latency = int((time.time() - start) * 1000)
            text = strip_reasoning(resp.choices[0].message.content or "")
            if text:
                print(f"[coach] {name} ({model}) ok in {latency} ms")
                return text, name, latency
            print(f"[coach] {name} ({model}) returned an empty answer in {latency} ms")
        except Exception as e:  # timeout, bad key, network… → next provider
            print(f"[coach] {name} ({model}) failed after {int((time.time() - start) * 1000)} ms: "
                  f"{type(e).__name__}: {e}")
    return None, None, 0


def strip_reasoning(text):
    """Remove "thinking" that some models put in the answer (<think>…</think>, gpt-oss channel markers)."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"^.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)  # opening tag cut off
    if "<think>" in text.lower():  # never closed: the answer was all reasoning
        text = text[: text.lower().index("<think>")]
    for marker in ("<|channel|>final<|message|>", "assistantfinal"):
        if marker in text:
            text = text.split(marker)[-1]
    return text.strip()


EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F]")


def clean_speech(text):
    """Plain spoken text: no markdown (**bold**, # titles, `code`, list dashes), no emoji, single spaces."""
    text = re.sub(r"\*\*|__|`+|^#+\s*|^\s*[-*•]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"(?<!\w)[*_](\S[^*_]*?)[*_](?!\w)", r"\1", text)  # *italic* / _italic_
    text = EMOJI.sub("", text)
    text = re.sub(r"(?<=[^\s.!?,:;])[ \t]*\n+\s*", ". ", text.strip())  # line breaks become sentence ends
    return re.sub(r"\s+", " ", text).strip()


def clean_values(obj):
    """clean_speech on every string inside parsed JSON."""
    if isinstance(obj, str):
        return clean_speech(obj)
    if isinstance(obj, list):
        return [clean_values(v) for v in obj]
    if isinstance(obj, dict):
        return {k: clean_values(v) for k, v in obj.items()}
    return obj


def parse_json(text):
    """Extract the JSON object/array from an LLM reply, ignoring reasoning, ```json fences and chatter."""
    text = strip_reasoning(text)
    text = re.sub(r"```(?:json)?", "", text).strip()
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

    start = time.time()
    text, provider, _ = chat(messages)
    if text:
        try:
            data = parse_json(text)
            say, highlight = clean_speech(str(data.get("say", ""))), data.get("highlight")
        except Exception:
            # Not JSON: keep only readable text (drop any JSON-looking fragments), no highlight.
            say, highlight = clean_speech(re.sub(r"[{}\[\]\"]|\bsay\b\s*:|\bhighlight\b\s*:.*", "", text)), None
        if say:
            return {
                "say": say[:400],
                "highlight": highlight if highlight in info["ids"] else None,
                "provider": provider,
                "latency_ms": int((time.time() - start) * 1000),  # what the user waited, retries included
            }
    cached = T["cache"][screen]
    return {"say": cached["say"], "highlight": cached["highlight"], "provider": "cache",
            "latency_ms": int((time.time() - start) * 1000)}
