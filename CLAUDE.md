# Learn, Practice, Adopt — Project brief for Claude Code

## Context
Hackathon MVP built in one day (GOMYCODE "Come Build with AI", 27 Sep 2026). Submission closes at 17:30 Tunis time, so we have about 4–5 hours of build time. Target awards: Kredete Financial Inclusion (primary) and Artefact Data & AI.

**Problem:** Morocco has 13.8 million mobile wallet accounts but very low usage (~1.4 transactions per account per year). Seniors and people with low literacy still pay bills in cash. The barrier is literacy and trust (fear of losing money, scams, OTP codes, reference numbers), not technology.

**Product:** a user learns what a digital payment is, practices paying a bill on a safe replica of a mobile wallet with fake money and an AI coach that speaks Moroccan Darija, then does it alone. Every session produces anonymous data. A dashboard shows the wallet provider where users struggle, why, and what to fix, with evidence.

**About me:** I'm an experienced software engineer (Java, .NET, Angular, React) but a beginner with AI and new to Streamlit. When you write AI-related code (LLM calls, prompts, Brev, speech), explain briefly what it does and why. Keep everything else short.

## How to work with me
- Work in the milestones below, in order. After each milestone, stop, tell me how to run and test it, and wait for my OK.
- Keep the code simple and readable. No abstractions we don't need. No extra frameworks.
- Ask before adding a dependency not listed here.
- The app must always stay runnable. Never leave it broken between milestones.
- Never put API keys in code. Read them from `st.secrets`.
- If something is ambiguous, pick the simplest option and tell me in one line.

## Stack
- Python 3.11, Streamlit (recent version, multipage via `pages/`), SQLite (`sqlite3` standard library)
- `openai` Python client for all LLM calls (NVIDIA Build and vLLM on Brev are both OpenAI-compatible)
- `pandas` and `plotly` for the dashboard
- Optional, milestone 6 only: `gTTS` for speech output; speech-to-text via a Whisper model on Brev
- Deploy target: Streamlit Community Cloud (free)

## Project structure
```
app.py              # home: consent screen + short lesson
pages/1_Practice.py # wallet replica + coach
pages/2_Dashboard.py# metrics, AI insights, recommendations
coach.py            # LLM calls, timeouts, fallback chain
analysis.py         # per-session and cross-session AI analysis
db.py               # SQLite schema + logging helpers
content.py          # screens text, validated coach content, cached answers per step
.streamlit/secrets.toml   # NVIDIA_API_KEY, BREV_URL, BREV_MODEL, BUILD_MODEL (gitignored)
requirements.txt
.gitignore
```

## Design rules (users are seniors and people who may not read)
- Large text (at least 22px body, 28px+ titles), high contrast, big full-width buttons. Inject CSS once via `st.markdown(unsafe_allow_html=True)`.
- One action per screen. No timers, no countdowns.
- Icons/emoji next to every button label.
- Reassuring tone everywhere: "This is practice, no real money."
- UI text in simple French with a Darija line under key instructions (Darija in Latin script, e.g. "Dkhel l'code li jak f SMS"). Put all texts in `content.py`, marked `# TO REVIEW BY TEAM` so a Darija speaker can fix them.

## The replica (pages/1_Practice.py)
A fictional generic wallet called "Mahfadati Wallet" (do not use real brand names or logos). Fake balance 500 MAD. Use case: paying an electricity bill.

Screens, stored in `st.session_state.step`:
1. `home` — balance and a "Pay a bill" button
2. `biller` — choose between "Électricité" and "Eau" (fictional biller "Régie Ville")
3. `reference` — a fake paper bill is shown (reference `EL-4471-2093`, amount 187.50 MAD); user types the reference
4. `confirm` — shows biller, reference, amount; button "Confirmer"
5. `otp` — a simulated SMS box appears: "Votre code est 4821. Ne le partagez jamais."; user types the code
6. `receipt` — success, receipt, and the value message: "2 minutes from home instead of a trip and a queue"

Simulated mistakes (must be handled and logged):
- Wrong reference → friendly error, coach explains where the reference is on the bill
- Wrong OTP → friendly error, coach explains what the code is
- "Back" / "I'm lost" button on every screen

Two modes, chosen at the start and stored in the session:
- `coached` — the coach speaks first on each screen with a short instruction, and the user can ask questions anytime
- `alone` — no automatic instructions; a small help button is still available but using it is logged

Variant for the before/after test, stored per session:
- `A` — original OTP screen wording (technical: "Saisissez le code OTP")
- `B` — improved wording ("Ce code confirme que c'est bien vous. Il n'envoie pas d'argent.")
- Chosen via a sidebar toggle (admin/tester use only).

## The AI coach (coach.py)
Function: `ask_coach(question, step, mode, history) -> (answer, source, latency_ms)`

- System prompt: patient coach for a senior paying a bill in a practice wallet; answers in simple Moroccan Darija (Latin script), max 2 short sentences; answers only from the validated content for the current step (passed in the prompt from `content.py`); never asks for real codes or personal data; never claims to perform actions; if unsure, says to contact the wallet's official support.
- Include the current step, the mode, and the last 4 turns of history.
- Fallback chain, each call with an 8-second timeout:
  1. Brev (`BREV_URL`, `BREV_MODEL`, a Darija model served with vLLM)
  2. NVIDIA Build (`https://integrate.api.nvidia.com/v1`, `BUILD_MODEL`)
  3. Cached answer for the current step from `content.py`
- Return `source` as `"brev"`, `"build"` or `"cache"` and log it.
- Also `auto_explain(step, error_type)` for automatic explanations after a mistake (same chain).
- Show a small caption under each coach answer with the source (useful for the demo).

## Data (db.py)
SQLite file `lpa.db`, created on startup if missing.

- `sessions(id TEXT PK, started_at, ended_at, mode, variant, completed INT, completed_alone INT, consent INT, age_range, education, is_simulated INT)`
- `events(id INTEGER PK, session_id, ts, step, type, detail)` — types: `step_enter`, `error_reference`, `error_otp`, `help_request`, `back`, `lost`, `complete`
- `turns(id INTEGER PK, session_id, ts, step, speaker, text, source, latency_ms)` — speaker: `user` or `coach`
- `analyses(session_id PK, json)` — per-session AI analysis

Session ids are random UUIDs. No names, no phone numbers, no audio stored.

## Consent (app.py)
Plain-language consent before starting: anonymous practice, fake money, only transcripts and clicks are saved. Optional fields (age range, education level) with a "Skip" button. Then a one-screen lesson: what a digital payment is and why the OTP code protects you ("a key sent only to you"), then "Start practice".

## AI analysis (analysis.py)
1. `analyze_session(session_id)` — at the receipt screen (or on "Finish"), send the transcript + that session's metrics to the LLM (NVIDIA Build is fine here). Require JSON only:
```json
{
  "struggle_steps": [{"step": "otp", "reason": "..."}],
  "question_themes": ["otp_meaning", "fear_losing_money"],
  "confidence": "hesitant | improving | confident",
  "completed_alone": true,
  "recommendation": "..."
}
```
   Parse safely (strip code fences, try/except); on failure store `{"error": "..."}` and move on.

2. `cross_session_insights(df_metrics, analyses)` — send aggregated numbers (not raw transcripts) plus a few short anonymized quotes. Rule in the prompt: **every recommendation must cite a number present in the data; no number, no recommendation.** Output JSON list, each item:
```json
{"finding": "...", "evidence": "...", "why": "...", "action": "...", "how_to_verify": "...", "confidence": "low | medium | high", "n_sessions": 0}
```
   Confidence must be "low" if fewer than 10 sessions.

## Dashboard (pages/2_Dashboard.py)
For a wallet product manager. Every chart shows N. Filter: include/exclude simulated sessions (excluded by default), filter by variant.

1. Top KPIs: sessions, completion rate, autonomy rate (completed in `alone` mode with zero errors and zero help), median time to complete
2. Funnel: % of sessions reaching each step
3. Friction by step: errors + help requests per step (bar chart)
4. Question themes (from analyses) with 2 anonymized example quotes each
5. Before/after: for the OTP step, help requests + errors per session, variant A vs B, side by side
6. Business card: "X% of test users could pay alone" labeled as a projection from test sessions
7. AI recommendations: button "Generate insights" → shows the evidence-based list above

## Dev helper
A sidebar button "Generate 10 simulated sessions" that inserts realistic fake sessions with `is_simulated = 1` (A has more OTP friction than B). Simulated data must always be labeled as such on the dashboard.

## Milestones
1. **Skeleton:** structure, requirements, CSS, consent + lesson, empty pages, db created. Runs locally.
2. **Replica:** all 6 screens, mistakes, mode + variant, event logging. No AI yet.
3. **Coach:** `coach.py` with NVIDIA Build first, cached fallback, auto-explain on mistakes, turns logged. Then add Brev as first option once I give you `BREV_URL`.
4. **Dashboard:** metrics, charts, simulated data button, filters.
5. **AI analysis:** per-session JSON + cross-session recommendations.
6. **Voice (only if time remains):** `st.audio_input` for push-to-talk, speech-to-text via Whisper on Brev, `gTTS` (Arabic) for coach answers, with a text box always available as fallback.
7. **Deploy:** check requirements, secrets, and give me the Streamlit Cloud steps.

## Out of scope
Real payments, real brands, user accounts, FastAPI backend, scam check, multiple languages switch, storing audio.
