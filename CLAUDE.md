# Learn, Practice, Adopt — Project brief for Claude Code (v2)

## Current state
Milestone 1 (skeleton, consent, lesson, SQLite) is already built and committed. Other milestones may be partly done. **Before coding, read the existing code, tell me in 5 lines what exists, then adapt it to this brief. Don't rewrite what works.**

## Context
One-day hackathon MVP (GOMYCODE "Come Build with AI", 27 Sep 2026). Submission closes at 17:30 Tunis time. Target awards: Kredete Financial Inclusion and Artefact Data & AI.

**Problem:** Morocco has 13.8 million mobile wallet accounts but very low usage (~1.4 transactions per account per year). Seniors and people with low digital literacy still pay bills in cash. The barrier is literacy and trust, not technology.

**Product:** a guided journey in three steps:
1. **Learn** — short spoken lessons: what a digital payment is, why the SMS code protects you
2. **Practice** — pay a bill on a safe wallet replica with fake money, with a voice coach
3. **Adopt** — do it again alone, then see the value: "2 minutes from home instead of a queue"

Every session produces anonymous data. A dashboard shows the wallet provider where users struggle, why, and what to fix, with evidence.

**Language for the demo: French only.** Darija is the post-hackathon upgrade. Keep all texts in `content.py`, keyed by language (`"fr"`), so another language can be added later without touching the logic.

**About me:** experienced software engineer, beginner with AI and Streamlit. Briefly explain AI-related code (LLM calls, prompts, speech). Keep everything else short.

## How to work with me
- Work milestone by milestone. After each one: run the code to check for errors, commit ("milestone N: ..."), then continue unless I said to stop.
- Keep the code simple. No new frameworks. Ask before adding a dependency not listed here.
- The app must always stay runnable.
- Never put keys in code; read them from `st.secrets`.
- If something is ambiguous, pick the simplest option and tell me in one line.

## Stack
- Python 3.11, Streamlit (recent, multipage via `pages/`), SQLite (`sqlite3`)
- `openai` client for all LLM calls (NVIDIA Build and Groq are OpenAI-compatible)
- `gTTS` for French speech output
- Groq Whisper for speech-to-text (via the `openai` client, `audio.transcriptions`)
- `pandas`, `plotly` for the dashboard
- Deploy: Streamlit Community Cloud

## Secrets (`.streamlit/secrets.toml`)
```toml
NVIDIA_API_KEY = ""
BUILD_BASE_URL = "https://integrate.api.nvidia.com/v1"
BUILD_MODEL = ""
GROQ_API_KEY = ""
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_CHAT_MODEL = ""
GROQ_STT_MODEL = ""
BREV_URL = ""      # optional, skipped when empty
BREV_MODEL = ""
```
Any empty provider is skipped silently.

## The coach: "like a video call with screen sharing"
This is the heart of the product. The user should feel like a patient person is on the phone, looking at the same screen, guiding them step by step.

**Persona:** "Salma", a warm, patient guide. Uses "vous". Short sentences, one idea at a time, everyday analogies (the SMS code is "a key sent only to you"). Never rushes, never blames. Praises each small success ("Très bien, c'est exactement ça."). Checks understanding ("C'est clair pour vous ?").

**Call behavior:**
1. **Call start:** first screen of practice is a big "📞 Appeler Salma" button. It also unlocks audio in the browser. Salma greets the user by voice.
2. **She speaks first on every screen:** a short spoken instruction, auto-played (`st.audio(..., autoplay=True)`).
3. **She sees the screen:** every coach call receives a "screen share" context: current screen, what is visible on it (fields, bill values, the SMS), what the user just did, number of errors on this step, mode. So she can say "The number is at the top of your bill, next to the date."
4. **She points at things:** the LLM returns JSON `{"say": "...", "highlight": "<element_id or null>"}`. The UI draws a thick yellow outline around the highlighted element (bill reference, OTP field, confirm button…), like a finger pointing on a shared screen.
5. **She reacts to mistakes by herself:** wrong reference or wrong code triggers a spoken, calm explanation plus a highlight, without the user asking.
6. **The user talks back:** one big mic button (`st.audio_input`), tap to talk. Transcribe with Groq Whisper (`language="fr"`), then answer. A small text box underneath is the fallback.
7. **No silence:** while the AI is thinking, immediately play a short pre-generated filler ("Hmm, un instant…"). Show a "Salma réfléchit…" indicator.
8. **Live subtitles:** a call-style panel shows the last 3 lines of the conversation (Salma / Vous), like captions.
9. **Call UI:** a small header bar "📞 En appel avec Salma · 02:14" with a "Raccrocher" button, and a round avatar with a soft pulse when she's speaking.

**Fixed lines vs AI:**
- Fixed lines (greeting, lesson, one instruction per screen, one reaction per mistake, fillers, praise) are written in `content.py` and **pre-generated to audio files with gTTS on first run**, cached in `audio_cache/` (gitignored). This keeps the call fast and reliable.
- Free questions and anything contextual go to the LLM, then gTTS on the fly.

**LLM rules (system prompt):**
- Answer in French, max 2 short sentences, spoken style (no lists, no markdown, no emoji).
- Only use the validated content for the current step (passed from `content.py`) and the screen context. Never invent fees, steps, or features.
- Never ask for real codes or personal data. Never claim to perform actions for the user.
- If unsure or off-topic, say so kindly and suggest the wallet's official support.
- Return JSON only: `{"say": "...", "highlight": "<id or null>"}`. Parse safely; on failure use the raw text with no highlight.

**Fallback chain (8-second timeout each):** Brev (if set) → NVIDIA Build → Groq → cached answer for the step from `content.py`. Log the provider and latency for every turn.

## The journey (modes)
Stored per session, in this order:
1. `learn` — Salma walks through 2–3 short lessons by voice; the user can ask questions.
2. `coached` — practice with Salma guiding every screen (behavior above).
3. `alone` — "Now try alone. I'm still on the line if you need me." Salma stays silent; the mic and a "Aide" button still work, but every use is logged as a help request.
4. `done` — value moment: time taken, "2 minutes from home instead of a trip and a queue", and a short spoken congratulation.

If the user makes 2+ errors or asks for help 2+ times in `alone`, Salma offers kindly to do one more coached round (log `repeat_coached`).

## The replica (`pages/1_Practice.py`)
Fictional generic wallet "Mahfadati Wallet" (no real brands). Fake balance 500 MAD. Use case: paying an electricity bill.

Screens (`st.session_state.step`), each element with a stable id for highlighting:
1. `home` — balance, "Payer une facture" (`btn_pay`)
2. `biller` — "Électricité" (`btn_elec`) / "Eau" (`btn_water`), biller "Régie Ville"
3. `reference` — fake paper bill image/card (`bill_card`, reference `EL-4471-2093` shown as `bill_ref`, amount 187,50 MAD); input `input_ref`
4. `confirm` — summary card (`summary`), "Confirmer" (`btn_confirm`)
5. `otp` — simulated SMS bubble (`sms`): "Votre code est 4821. Ne le partagez jamais."; input `input_otp`
6. `receipt` — receipt (`receipt`), success

Mistakes (handled and logged): wrong reference, wrong code, and a "Je suis perdu(e)" button on every screen.

**Variant for the before/after test** (sidebar, tester only):
- `A` — OTP screen says "Saisissez le code OTP"
- `B` — "Tapez le code reçu par SMS. Il confirme que c'est bien vous. Il n'envoie pas d'argent."

## Design rules (seniors, low literacy)
- Atkinson Hyperlegible font, body ≥ 22px, titles ≥ 28px, high contrast, big full-width buttons, icons on every button.
- One action per screen. No timers or countdowns (the call duration display is fine).
- Reassurance visible on every practice screen: "Entraînement · argent fictif".
- Mobile-first layout: the demo will be shown on a phone.

## Data (`db.py`)
- `sessions(id, started_at, ended_at, mode_reached, variant, completed, completed_alone, consent, age_range, education, is_simulated)`
- `events(id, session_id, ts, mode, step, type, detail)` — types: `step_enter`, `error_reference`, `error_otp`, `help_request`, `lost`, `repeat_coached`, `hangup`, `complete`
- `turns(id, session_id, ts, mode, step, speaker, text, input_type, provider, latency_ms, highlight)` — speaker `user`/`coach`; input_type `voice`/`text`/`fixed`
- `analyses(session_id, json)`

Anonymous UUIDs. No names, phone numbers, or audio stored (delete audio after transcription).

## AI analysis (`analysis.py`)
1. `analyze_session(session_id)` at the end: transcript + metrics → JSON only:
   `{"struggle_steps":[{"step":"otp","reason":"..."}], "question_themes":["..."], "confidence":"hesitant|improving|confident", "completed_alone":true, "recommendation":"..."}`
2. `cross_session_insights(...)`: aggregated numbers + a few short anonymized quotes → list of
   `{"finding","evidence","why","action","how_to_verify","confidence","n_sessions"}`.
   Rule: **every recommendation must cite a number present in the data**. Confidence is "low" under 10 sessions.

## Dashboard (`pages/2_Dashboard.py`)
For a wallet product manager. Every chart shows N. Filters: simulated sessions (excluded by default), variant.
1. KPIs: sessions, % reaching each mode (learn → coached → alone → done), autonomy rate (alone completed with 0 errors and 0 help), median time
2. Journey funnel: Learn → Practice → Adopt
3. Friction by step: errors + help per step
4. Question themes with 2 anonymized quotes each
5. Before/after at the OTP step: A vs B
6. Business card: "X% of test users could pay alone" (labeled as a projection)
7. "Générer les recommandations" → evidence-based list

Sidebar dev button: "Generate 10 simulated sessions" (`is_simulated = 1`, A has more OTP friction than B), always labeled as simulated.

## Milestones
1. ✅ Skeleton (done)
2. **Replica + journey:** 6 screens with element ids, mistakes, modes learn → coached → alone → done, variant, event logging. Fixed coach lines shown as text for now.
3. **Coach brain:** `coach.py` with screen-share context, JSON `{say, highlight}`, fallback chain, highlight rendering, auto-reaction to mistakes, turns logged.
4. **Call experience:** gTTS pre-generation + cache, auto-play, call start button, header bar, avatar, subtitles, filler audio, mic with Groq Whisper, text fallback.
5. **Dashboard + simulated data.**
6. **AI analysis + recommendations.**
7. **Deploy:** requirements, `.gitignore` (add `audio_cache/`), Streamlit Cloud steps.

## Out of scope
Real payments, real brands, Darija (post-demo), user accounts, FastAPI backend, continuous listening / interruptions, storing audio.
