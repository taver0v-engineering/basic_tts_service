# Read Aloud

A minimal, free, self-hosted text-to-speech reader:
- **Backend** (`backend/`): FastAPI service that wraps [Piper TTS](https://github.com/OHF-Voice/piper1-gpl) (CPU-only, no GPU needed). Accepts either raw text or a URL (extracts the article server-side), supports multiple languages/voices, auto-detects the text's language when you don't pick one, and caps audio at 10 minutes with a friendly error if it's longer.
- **Frontend** (`frontend/index.html`): paste an article *or* a link (mutually exclusive — whichever has content is the active source), pick a language/voice (or leave on Auto), press **Convert**, then once it's ready press **Play** (same button doubles as Pause) — plus Restart, skip ±10s/±30s, and a draggable seek bar to jump anywhere in the audio. A status indicator always shows whether conversion is in progress, ready, playing, or failed.

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
# get real language auto-detection + selection working. Below are several
# per language so you can compare quality/style; skip whichever you don't want.
# Browse the full catalog and listen to samples at:
# https://rhasspy.github.io/piper-samples/ and https://huggingface.co/rhasspy/piper-voices

# English (US)
python -m piper.download_voices en_US-lessac-medium
python -m piper.download_voices en_US-amy-medium
python -m piper.download_voices en_US-libritts_r-medium
python -m piper.download_voices en_US-ryan-medium
python -m piper.download_voices en_US-kristin-medium

# English (UK)
python -m piper.download_voices en_GB-alan-medium
python -m piper.download_voices en_GB-vctk-medium
python -m piper.download_voices en_GB-northern_english_male-medium

# German
python -m piper.download_voices de_DE-thorsten-medium
python -m piper.download_voices de_DE-eva_k-x_low
python -m piper.download_voices de_DE-kerstin-low
python -m piper.download_voices de_DE-ramona-low

# French
python -m piper.download_voices fr_FR-siwis-medium
python -m piper.download_voices fr_FR-gilles-low
python -m piper.download_voices fr_FR-upmc-medium

# Spanish
python -m piper.download_voices es_ES-davefx-medium
python -m piper.download_voices es_ES-carlfm-x_low
python -m piper.download_voices es_MX-ald-medium

# Italian
python -m piper.download_voices it_IT-riccardo-x_low
python -m piper.download_voices it_IT-paola-medium

# Portuguese
python -m piper.download_voices pt_BR-faber-medium
python -m piper.download_voices pt_BR-edresson-low
python -m piper.download_voices pt_PT-tugao-medium

# Dutch
python -m piper.download_voices nl_NL-mls-medium
python -m piper.download_voices nl_BE-nathalie-medium

# Polish
python -m piper.download_voices pl_PL-darkman-medium
python -m piper.download_voices pl_PL-gosia-medium

# Hungarian
python -m piper.download_voices hu_HU-imre-medium
python -m piper.download_voices hu_HU-anna-medium

# A few more languages worth knowing about (add matching Voice() entries
# in backend/main.py if you download these):
# Russian:    ru_RU-irina-medium, ru_RU-denis-medium
# Swedish:    sv_SE-nst-medium
# Danish:     da_DK-talesyntese-medium
# Finnish:    fi_FI-harri-medium
# Czech:      cs_CZ-jirka-medium
# Romanian:   ro_RO-mihai-medium
# Turkish:    tr_TR-fahrettin-medium
# Ukrainian:  uk_UA-lada-x_low
# Chinese:    zh_CN-huayan-medium
# Arabic:     ar_JO-kareem-medium

cd ..
uvicorn main:app --host 0.0.0.0 --port 8000
```

> **Note:** voice IDs occasionally get renamed/reorganized upstream. If a
> `download_voices` command above 404s, check the current exact name at
> https://rhasspy.github.io/piper-samples/ or the `voices.json` in
> https://huggingface.co/rhasspy/piper-voices before assuming it's gone.

Check it's alive: open `http://localhost:8000/health` — should show `"status": "ok"`
and a `voices_available` count. Open `http://localhost:8000/voices` to see exactly
which ones the frontend will offer (only voices whose `.onnx` file is actually
present show up — you don't have to download all of them, just skip the ones
you don't want).

Each voice you download beyond the first also needs a matching `Voice(...)`
entry added to the `VOICES` list in `backend/main.py` (a handful of common
ones are already there) — copy the pattern for any extra voice/language you add.

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

## Converting from a link instead of pasted text

- The frontend has two input fields: the text box and a URL box. They're
  mutually exclusive — typing in one disables the other, and a small
  indicator ("Source: Text" / "Source: Link") always shows which is active.
- When you press **Convert** with a link entered, the backend fetches that
  page and extracts just the main article content (via
  [trafilatura](https://github.com/adbar/trafilatura), stripping nav/ads/
  comments), then treats that extracted text exactly like pasted text —
  same language detection, same voice selection, same 10-minute cap.
- If the page can't be fetched or no readable article content is found, you
  get a plain-language error (e.g. "Could not find readable article content
  at that link — try pasting the text directly instead") rather than a raw
  exception.
- The response also reports the extracted article's title (`X-Source-Title`
  header) when available, which the frontend shows next to "Ready to play".

## Frontend playback controls

- **Convert** only does the text-to-speech conversion — it does not start
  playback automatically. Progress is shown by the status dot/text (gray =
  idle, pulsing amber = converting, green = ready, pulsing amber again =
  playing, red = error).
- **Play** is a single toggle button that becomes enabled once conversion
  finishes; it doubles as **Pause** while audio is playing.
- There's no separate Stop button — use Restart (jumps to 0:00) or drag the
  seek bar to wherever you want.

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
