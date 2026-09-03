# Read Aloud

A minimal, free, self-hosted text-to-speech reader:
- **Backend** (`backend/`): FastAPI service that wraps [Piper TTS](https://github.com/OHF-Voice/piper1-gpl) (CPU-only, no GPU needed). Supports multiple languages/voices, auto-detects the text's language when you don't pick one, and caps audio at 10 minutes with a friendly error if your text is longer.
- **Frontend** (`frontend/index.html`): paste an article, pick a language/voice (or leave on Auto), press "Convert & Play", then pause/resume/stop, restart, skip ±10s/±30s, or drag the seek bar to jump anywhere in the audio.

## 1. Run the backend locally

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

mkdir -p models
cd models

# Download whichever voices you want to offer. At minimum, download one —
# the app works fine with just en_US-lessac-medium — but download more to
# get real language auto-detection + selection working:
python -m piper.download_voices en_US-lessac-medium
python -m piper.download_voices en_GB-alan-medium
python -m piper.download_voices de_DE-thorsten-medium
python -m piper.download_voices fr_FR-siwis-medium
python -m piper.download_voices es_ES-davefx-medium
python -m piper.download_voices it_IT-riccardo-x_low
python -m piper.download_voices pt_BR-faber-medium
python -m piper.download_voices nl_NL-mls-medium
python -m piper.download_voices pl_PL-darkman-medium
python -m piper.download_voices hu_HU-imre-medium

cd ..
uvicorn main:app --host 0.0.0.0 --port 8000
```

Check it's alive: open `http://localhost:8000/health` — should show `"status": "ok"`
and a `voices_available` count. Open `http://localhost:8000/voices` to see exactly
which ones the frontend will offer (only voices whose `.onnx` file is actually
present show up — you don't have to download all of them, just skip the ones
you don't want).

## 2. Open the frontend

Just open `frontend/index.html` in a browser (double-click it, or serve it with
any static file server). By default it points at `http://localhost:8000/synthesize`
— change the "Backend URL" field at the bottom of the page once you deploy the
backend somewhere public.

## 3. Deploying the backend for free

Piper is lightweight (no GPU, small model, low RAM), so it fits comfortably on:

- **Hugging Face Spaces (Docker, CPU Basic)** — 2 vCPU / 16GB RAM, free forever,
  sleeps after 48h of inactivity. Easiest path: create a Space, add a
  `Dockerfile` that installs `requirements.txt`, downloads the voice model at
  build time, and runs `uvicorn main:app --host 0.0.0.0 --port 7860`.
- **Render (free web service)** — 512MB RAM, free, sleeps after 15 minutes of
  inactivity (a few seconds to wake up).
- **Oracle Cloud Always Free (Ampere A1 VM)** — a real always-on VPS, no sleep,
  ARM architecture (Piper supports ARM/aarch64 fine). Best option if you want
  zero cold-start delay for users.

Whichever you pick, update `ALLOWED_ORIGINS` in `backend/main.py` to your
actual frontend origin instead of `"*"` before making it public.

## How language/voice selection works

- The frontend's Language dropdown is built from whatever `/voices` reports
  (i.e. whichever models you actually downloaded). "Auto" is always the default.
- If you leave Language/Voice on "Auto", the backend runs language detection
  (`langdetect`) on the pasted text and picks the first downloaded voice that
  matches. If detection fails or no matching voice is downloaded, it falls
  back to `DEFAULT_FALLBACK_VOICE_ID` in `backend/main.py` (English by default).
- Picking a specific voice from the dropdown skips detection entirely and
  uses exactly that voice.
- Add more languages by downloading more voices (see above) and adding a
  matching `Voice(...)` entry to the `VOICES` list in `backend/main.py`.

## The 10-minute limit

- `MAX_AUDIO_SECONDS` in `backend/main.py` (default: 600s / 10 minutes) is
  checked against the *actual* generated audio duration, not just character
  count — so it's accurate regardless of voice/language speaking rate.
- If a text would produce longer audio, the backend returns a 413 response
  with a plain-language message telling the user roughly how many characters
  to cut. The frontend displays that message as-is in the status line — no
  raw errors or stack traces reach the user.
- `MAX_INPUT_CHARS` (default 40,000) is just a cheap upfront sanity check to
  reject obviously-too-long pastes before spending time synthesizing them.

## Notes

- Piper (`piper-tts`) is GPL-3.0 licensed. If you're distributing this whole
  project as open source, licensing your own code under GPL-3.0 keeps things
  simple and fully compatible.
