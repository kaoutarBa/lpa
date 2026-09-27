# Learn, Practice, Adopt

A practice mobile wallet with a voice coach, Salma, who helps older people learn to pay a bill.
Everything happens inside one call: consent → optional questions → assisted mode (Salma explains a concept,
then you apply it in the app) → try alone (Salma stays on the line) → done.
Sessions are anonymous; a PIN-protected dashboard shows the wallet provider where people struggle and what to fix.

## Run locally
```bash
python -m pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # then fill in your keys
python -m streamlit run app.py
```
Works without any key: Salma falls back to pre-written answers, text only if speech is unavailable.

## Files
- `app.py` navigation (user view = the call only; provider view with PIN adds the dashboard)
- `pages/1_Practice.py` the call + the fictional payment app · `pages/2_Dashboard.py` provider dashboard
- `ear.py` + `salma_ear.js` continuous listening (Web Speech API) and the call bar
- `coach.py` LLM calls + fallback chain · `voice.py` gTTS + Whisper · `analysis.py` AI analysis · `progress.py` autonomy
- `content.py` all texts (keyed by language) · `db.py` SQLite (`lpa.db`, created on start)
- `check_ai.py` live check of your keys: `python check_ai.py` (one coach call + one analysis call)

## Provider view
Open the sidebar (collapsed by default, not available during a call), choose **Vue : Fournisseur** at the bottom
and type `PROVIDER_PIN`. The dashboard only exists in that view.

## Deploy (Streamlit Community Cloud)
1. share.streamlit.io → **Create app** → repo `kaoutarBa/lpa`, branch, main file `app.py`.
2. **Advanced settings**: Python 3.11 or 3.12; paste your secrets (same format as `secrets.toml.example`).
3. Deploy. Note: `lpa.db` and `audio_cache/` are reset when the app restarts.
