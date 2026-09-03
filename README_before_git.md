# Read Aloud

A minimal, free, self-hosted text-to-speech reader:
- **Backend** (`backend/`): FastAPI service that wraps [Piper TTS](https://github.com/OHF-Voice/piper1-gpl) (CPU-only, no GPU needed).
- **Frontend** (`frontend/index.html`): a single HTML page — paste an article, press "Convert & Play", pause/resume/stop.

## 1. Run the backend locally

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Download a voice model (one-time). This creates backend/models/... automatically
# if you point the download at that folder — see note below.
python -m piper.download_voices en_US-lessac-medium

# Make sure the .onnx file ends up at backend/models/en_US-lessac-medium.onnx
# (create the models/ folder and move the downloaded files there if needed).

uvicorn main:app --host 0.0.0.0 --port 8000
```

Check it's alive: open `http://localhost:8000/health` — should show `"status": "ok"`.

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

## Notes

- `MAX_CHARS` in `backend/main.py` caps request size (default 20,000 characters)
  so one huge paste can't tie up the server — adjust as needed.
- Swap voices by downloading a different one with
  `python -m piper.download_voices <voice-name>` (browse options at
  https://github.com/OHF-Voice/piper1-gpl) and updating `MODEL_PATH`.
- Piper (`piper-tts`) is GPL-3.0 licensed. If you're distributing this whole
  project as open source, licensing your own code under GPL-3.0 keeps things
  simple and fully compatible.
