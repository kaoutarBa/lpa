# Learn, Practice, Adopt

A practice mobile wallet with a voice coach ("Salma") that helps older people learn to pay a bill:
**Learn** (short spoken lessons) → **Practice** (guided, fake money) → **Adopt** (alone, then see the value).
Every session is anonymous; a dashboard shows the wallet provider where users struggle and what to fix.

## Run locally
```bash
python -m pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # then fill in your keys
python -m streamlit run app.py
```
Works without any key: Salma falls back to pre-written answers, text only if speech is unavailable.

## Files
- `app.py` consent · `pages/1_Practice.py` the call + wallet replica · `pages/2_Dashboard.py` metrics and recommendations
- `coach.py` LLM calls + fallback chain · `voice.py` gTTS + Whisper · `analysis.py` AI analysis
- `content.py` all texts (keyed by language) · `db.py` SQLite (`lpa.db`, created on start)

## Deploy (Streamlit Community Cloud)
1. share.streamlit.io → **Create app** → repo `kaoutarBa/lpa`, branch, main file `app.py`.
2. **Advanced settings**: Python 3.11 or 3.12; paste your secrets (same format as `secrets.toml.example`).
3. Deploy. Note: `lpa.db` and `audio_cache/` are reset when the app restarts.
