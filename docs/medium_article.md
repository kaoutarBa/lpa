# Salma Is on the Line: Building a Voice Coach That Teaches Seniors to Pay a Bill With Their Phone

*How we built "Learn, Practice, Adopt" in one hackathon day with Streamlit, open LLMs and a very patient AI — and what our own tests taught us along the way.*

---

## 13.8 million wallets, 1.4 transactions a year

Morocco has around **13.8 million mobile wallet accounts**. Yet each account is used about **1.4 times a year**. Walk into any bill-payment office at the end of the month and you will see why: the queue is full of people, many of them older, holding a paper bill and cash.

The easy explanation is "they don't have smartphones" or "the apps are bad". Talk to them for five minutes and you hear something else:

- *"What if I press the wrong button and lose my money?"*
- *"They sent me a code. Should I give it to someone?"*
- *"Where is the number they're asking for?"*

The barrier isn't technology. It's **literacy and trust**. People don't need a better app first. They need someone patient enough to sit next to them the first time.

That was our starting point for the GOMYCODE *"Come Build with AI"* hackathon: **what if that patient person was a phone call away, available to everyone, at any time?**

---

## The idea: a phone call, not a tutorial

Our product, **Learn, Practice, Adopt**, puts the user in a call with **Salma**, a warm, patient voice coach. On the screen, there is only a fictional mobile wallet, *Mahfadati*, with **500 MAD of fake money** and a paper electricity bill to pay.

The whole journey happens inside that one call:

1. **Consent, by voice.** Salma introduces herself and asks if it's OK to start. The session is anonymous, the money is fake and the voice is never recorded. You can simply say *"oui"*.
2. **A few optional questions**: age, school level and occupation. Salma uses your first name during the call, but it is never stored.
3. **Assisted mode: learn a concept, then use it right away.** Before each screen, Salma explains the one idea you need, in plain words:
   - *Paying from your phone* is like paying at the counter, without the trip and the queue.
   - *The bill reference* is your bill's name. It is written at the top, next to the date.
   - *Check before you pay*: the name, the reference and the amount. Nothing is paid before the code.
   - *The SMS code* is "a key sent only to you". It proves it's you, it doesn't send money, and you never give it to anyone.

   Then you apply the idea on the wallet screen, while she points at the right button with a yellow outline, like a finger on a shared screen.
4. **Now try alone.** *"I'm still on the line if you need me."* Salma goes quiet but keeps watching. If you hesitate for 20 seconds, she gently relaunches you. After two slips, she offers one more guided round.
5. **The value moment.** You paid a bill from home, and we show you how long it took. *Two minutes from home, instead of a trip and a queue.*
6. **Five short questions** at the end: did you understand, do you feel able to do it alone next time, do you feel safe with the SMS code, which step was hardest, will you try with a real bill.

Every session produces anonymous data. On the other side, a **dashboard for the wallet provider** shows where people struggle, why, and what to fix, with evidence.

---

## The stack (and why it's boring on purpose)

We had one day, so every choice favoured "works on the first try":

- **Streamlit**, for both the app and the dashboard, in pure Python.
- **SQLite**, one file that is created on startup.
- **LLMs through one client.** NVIDIA Build and Groq both speak the OpenAI API, so a single `openai` client talks to all of them. We only swap `base_url`, the key and the model name.
  - The coach uses **Groq `openai/gpt-oss-20b`** first, with `reasoning_effort="low"`, and **NVIDIA `mistral-nemotron`** as backup.
  - The session analysis uses **NVIDIA `nemotron-3-super-120b`**, a bigger model, because nobody is waiting on the phone for it.
- **Groq Whisper** for speech-to-text and **gTTS** for Salma's voice.
- **Streamlit Community Cloud** for deployment.

On our first live test, **the coach answered in 744 ms**, fast enough to feel like a conversation. The analysis of a session took **11.7 s**, which is fine because it runs in the background once the payment is done.

---

## Making an LLM "see" the screen

An LLM can't see pixels, so we describe the screen to it, like narrating a screen share over the phone. Every call to the coach includes:

- the current screen and everything visible on it, each element with a stable id: `bill_ref`, `input_otp`, `btn_confirm`…
- what the user just did (*"typed EL-44, which is wrong"*)
- how many mistakes they made on this screen
- the mode: assisted or alone.

The model must answer in JSON:

```json
{"say": "The number is at the top of your bill, next to the date.", "highlight": "bill_ref"}
```

`say` is spoken aloud. `highlight` draws a thick yellow outline around that element. That second field is what turns a chatbot into a guide: Salma doesn't just tell you where things are, she *shows* you.

The system prompt is short and strict. Answer in French with at most two short sentences, in a spoken style with no lists and no emoji. Use only the validated facts for this screen, which we pass in. Never ask for a real code or personal data, and never pretend to act for the user. If you're unsure, say so kindly and point to the wallet's official support.

Two practical lessons:

**1. Clean everything.** Some models "think out loud" (`<think>…</think>`), wrap JSON in markdown fences or add `**bold**`. We strip all of it before parsing, showing or speaking a single word. A senior should never hear a TTS engine read "asterisk asterisk".

**2. Never let the call go silent.** Providers are tried in order with an **8-second timeout** each. If every provider fails, Salma falls back to a **pre-written answer for the current screen**. She never goes quiet. While the model is thinking, a short pre-recorded filler plays: *"Hmm, un instant…"*

Fixed lines (the greeting, concept explanations, one instruction per screen and the first reaction to a mistake) are written by hand and **pre-generated to audio** at startup. Only free questions go to the LLM. That keeps the call fast, cheap and predictable, and it keeps the AI where it adds value: answering *your* question about *your* screen.

---

## What our own tests changed (a lot)

The first version worked. It was also wrong in ways we only saw by using it ourselves.

**"The page is overloaded."** Version one showed the conversation as a written transcript, audio players, a text box, a mic button and a "source" caption for the demo. We had built a developer's view of a voice app. We removed everything that wasn't the fictional payment app. Salma is **heard, not read**. The only thing on top is a small call bar: avatar, call duration, status (*listening / speaking / thinking*) and a red *Hang up* button.

**"Why does it need a separate mic button? It should be one call."** A tap-to-talk button is exactly the kind of interface that loses a nervous user. So we moved to **continuous listening**. The user just talks, like on the phone.

**"Salma doesn't hear me."** Our first continuous version relied on the browser's built-in speech recognition (the Web Speech API). In Chrome, that API sends audio to Google's servers, and on the tester's machine it silently failed. We replaced it with something we control:

- The page opens the microphone and measures the volume every 50 ms against the room's noise level.
- When someone starts talking, it records. After about 0.9 s of silence, it stops.
- The recorded phrase goes to Python, which transcribes it with **Groq Whisper** (French, with a short context prompt). The audio is then dropped: nothing is stored.
- While Salma speaks, the mic pauses, so she never answers herself.

It works in any modern browser. We also learned to filter Whisper's favourite hallucination: in near-silence, it sometimes "hears" *"Sous-titres réalisés par…"*.

**"The screens are mixed."** When a step changed, the old screen stayed visible under the new one for a second or two. Streamlit keeps previous elements on screen while it recomputes, and we were generating Salma's voice *before* drawing the new screen. We fixed it three ways: each screen now gets its own container, which replaces the old one as a whole; leftover elements are hidden; and the voice is generated *after* the screen is drawn. With a deliberately slowed-down voice, the new screen now appears in under 0.4 s.

**"Start the call before the questions."** Originally, consent and the profile questions were a form you filled in *before* calling Salma. But the people we're building for might need help from the very first screen. Now the call starts first, and Salma walks you through consent too.

**"Explain, then apply."** Our first flow had three lessons up front, then practice. Moving each concept to the moment it's needed, just before the screen where you use it, made the whole thing feel less like school and more like someone sitting next to you.

None of these were technical breakthroughs. They were all the same lesson: **the product is the experience of a nervous first-timer, not the features.**

---

## A dashboard that has to earn its numbers

Our first dashboard had a funnel, a friction chart, question themes, an A/B test and a levels chart. It was a lot of information that said very little. We rebuilt it around one question: *what should the wallet team fix next?*

It now shows four figures:

- **Pay alone after one session**: how many completed the alone attempt without help.
- **Help needed, 1st vs 2nd attempt**: requests for help plus Salma's relaunches, per person, guided versus alone.
- **Blocking screen #1**: where people *still* struggle when alone.
- **Abandons**: how many gave up, and where.

Under them sits **one chart**: for each screen, the share of sessions in difficulty on the 1st attempt (with Salma) versus the 2nd (alone). The reading rule is written right under it: *what drops between attempts is learned with Salma; what stays high must be fixed in the app.* That single sentence separates "this is a training problem" from "this is a product problem".

Then comes **what people say**, from the end-of-call questions, next to what they **actually did**. For example: *"Say they can do it alone: 2 of 3, and of those, 2 really did it without help."*

Finally, the AI writes at most **three recommendations**, and we enforce two rules in code, not only in the prompt:

- **No number, no recommendation.** Every item's evidence must cite a number that exists in the data. If it doesn't, the item is dropped.
- **Honesty with small samples.** Under 10 sessions we write "3 of 5", not "60%", and confidence is forced to "low". Under 3 sessions, the dashboard simply says there isn't enough data yet.

The dashboard is hidden from users: there's no menu entry and no URL. Providers switch to it with a PIN.

---

## Designing for people who may not read

A few rules we held onto, even under time pressure:

- **The Atkinson Hyperlegible font**, text of 22 px or more, high contrast and big full-width buttons with an icon on each.
- **One action per screen.** No timers, no countdowns (the call duration is the only clock).
- **"Training · fake money"** visible on every screen.
- **Never blame.** A wrong reference gets *"That's not the right number. No problem, try again."* The first mistake gets a calm, pre-written explanation. A second mistake on the same screen gets a contextual AI answer that knows what you typed.
- **Mobile first.** The demo runs on a phone.

---

## What we'd do next

- **Darija.** The demo is French only, but every text lives in one `content.py` file, keyed by language, so Moroccan Darija is a translation away, not a rewrite. Salma speaking Darija is the real product.
- **Real pilots**, with a wallet provider and an association working with seniors, to replace our own test sessions with real ones.
- **Barge-in**: letting the user interrupt Salma mid-sentence, like a real call.
- **Persistent storage**, because on the free hosting tier the SQLite file resets whenever the app restarts.

---

## The takeaway

The most useful thing AI did in this project wasn't generating text. It was being **patient at scale**: answering *"where is the number?"* for the fifth time with the same calm voice, pointing at the right spot on the screen, and noticing when someone froze for 20 seconds.

The second most useful thing was turning those moments into **evidence** a product team can act on: not *"users find it confusing"*, but *"1 in 3 still struggle at the reference screen when alone, so fix that screen."*

Financial inclusion doesn't start with a new app. It starts with a first payment that didn't feel scary.

---

*Built at the GOMYCODE "Come Build with AI" hackathon, September 2026. Stack: Python, Streamlit, SQLite, Groq (gpt-oss-20b, Whisper), NVIDIA Build (Mistral Nemotron, Nemotron Super), gTTS. Coded with the help of Claude Code.*
