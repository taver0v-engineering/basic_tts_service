# Read Aloud

A minimal, free, self-hosted text-to-speech reader:
- **Backend** (`backend/`): FastAPI service that wraps [Piper TTS](https://github.com/OHF-Voice/piper1-gpl) (CPU-only, no GPU needed). Accepts either raw text or a URL (extracts the article server-side), supports multiple languages/voices, auto-detects the text's language when you don't pick one, and rejects text whose *estimated* speaking time is over a configurable cap (default 10 minutes) before running the (comparatively expensive) synthesis step. All of this is controlled by `backend/config.json`, read once at startup.
- **Frontend** (`frontend/index.html`): paste an article *or* a link (mutually exclusive — whichever has content is the active source, with a one-click **Clear** next to each field to switch without deleting anything by hand), pick a language/voice (or leave on Auto), press **Convert** (or **Stop** to cancel mid-conversion), then once it's ready press **Play** (same button doubles as Pause) — plus Restart, skip ±10s/±30s, and a draggable seek bar to jump anywhere in the audio. A status indicator always shows whether conversion is in progress (with a live timer), ready (with the total conversion time), playing, cancelled, or failed. A theme toggle in the header switches between dark (default) and light; it follows your browser/OS preference automatically until you override it.

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
python main.py                              # reads host/port from config.json
# -- or, to override host/port on the command line instead --
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
any static file server). By default it points at `http://localhost:8000`
(matching `config.json`'s default `host`/`port`) — change the "Backend URL"
field at the bottom of the page once you deploy the backend somewhere public.
That field is only editable when the backend's `environment` is `"test"`; in
`"production"` it's fixed and shown read-only, based on what `GET /config`
reports.

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

Whichever you pick, update `allowed_origins` in `backend/config.json` to your
actual frontend origin instead of `"*"` before making it public, and set
`"environment": "production"` (see below) so the frontend won't let anyone
point it at a different backend.

## Configuration (`backend/config.json`)

The backend reads `config.json` (next to `main.py`) once at startup. If the
file is missing or unreadable, it falls back to sensible defaults and prints
a note to the console — it never fails to start over a bad config file.

```json
{
  "environment": "test",
  "host": "localhost",
  "port": 8000,
  "allowed_origins": ["*"],
  "max_audio_minutes": 10,
  "estimated_chars_per_second": 14,
  "default_theme": "dark"
}
```

| Key | Effect |
| --- | --- |
| `environment` | `"test"` leaves the frontend's **Backend URL** field editable, so you can point it at any backend while developing. `"production"` locks that field so end users can't repoint the frontend elsewhere. The backend exposes this (plus the fields below marked *(also in `/config`)*) via `GET /config`, which the frontend reads on load. |
| `host`, `port` *(also in `/config`)* | Used by `python main.py` to start uvicorn, and match the frontend's default Backend URL (`http://localhost:8000`) out of the box. Change both together if you move the backend elsewhere, or just pass `--host`/`--port` to `uvicorn` directly. |
| `allowed_origins` | Passed straight through to FastAPI's CORS middleware. Keep as `["*"]` for local development; set it to your real frontend origin(s) before deploying publicly. |
| `max_audio_minutes` *(also in `/config`)* | The speaking-time cap, in minutes — see "The speaking-time limit" below. |
| `estimated_chars_per_second` | Average speaking rate used only to *estimate* audio length before running synthesis (see below). 14 is a reasonable default; tune it if you find the estimate is consistently too strict or too lax for your voices. |
| `default_theme` *(also in `/config`)* | Fallback dark/light theme for the frontend, used only if the browser can't report its own color-scheme preference (see "Theme" below). |

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

- When you press **Convert** with a link entered, the backend fetches that
  page and extracts just the main article content (via
  [trafilatura](https://github.com/adbar/trafilatura), stripping nav/ads/
  comments), then treats that extracted text exactly like pasted text —
  same language detection, same voice selection, same speaking-time cap.
- If the page can't be fetched or no readable article content is found, you
  get a plain-language error (e.g. "Could not find readable article content
  at that link — try pasting the text directly instead") rather than a raw
  exception.
- The response also reports the extracted article's title (`X-Source-Title`
  header) when available, which the frontend shows next to "Ready to play".

## Switching between text and a link

- The frontend has two input fields: the text box and a URL box. They're
  mutually exclusive — whichever has content disables the other — but you're
  never forced to manually select-and-delete to switch: a small **Clear ✕**
  button appears above whichever field is currently active, and clicking it
  empties that field and immediately re-enables the other one.
- The indicator below the fields ("Source: Text" / "Source: Link") is dim and
  neutral when there's no input yet (including right after startup or right
  after clearing a field), and only picks up an accent color once a source is
  actually active — so an empty state never reads like something's wrong.

## Frontend playback controls

- **Convert** kicks off the text-to-speech conversion — it does not start
  playback automatically. While converting, the button is replaced by a
  **Stop** button that cancels the in-flight request (the backend also stops
  the underlying Piper process immediately rather than letting it run to
  completion). Progress is shown by the status dot/text (gray = idle, pulsing
  amber = converting — with a live running timer, green = ready — including
  the total time the conversion took, pulsing amber again = playing, gray =
  stopped, red = error).
- **Play** is a single toggle button that becomes enabled once conversion
  finishes; it doubles as **Pause** while audio is playing.
- There's no separate Stop button for *playback* — use Restart (jumps to
  0:00) or drag the seek bar to wherever you want. ("Stop" during conversion
  is a different action — see above.)

## Theme

- A toggle button (🌙/☀️) in the header switches between the dark theme
  (default) and a light theme.
- On first visit, the theme follows your browser/OS's `prefers-color-scheme`
  setting automatically — you shouldn't need to touch the toggle at all
  unless you want something different from your system setting. Once you
  click the toggle, your explicit choice is remembered (in that browser) and
  takes priority over the OS setting from then on.
- If a browser doesn't support `prefers-color-scheme` detection at all, the
  frontend falls back to `default_theme` from the backend's `config.json`
  (itself defaulting to `"dark"`).

## The speaking-time limit

The point of this cap is to protect the backend host from long-running
conversions — not just to limit how long the resulting audio is — so it's
enforced *before* synthesis runs, not after:

- Before calling Piper, the backend estimates how many seconds of speech the
  text will produce, using `estimated_chars_per_second` from `config.json`
  (a simple, voice-agnostic average — it only needs to be a good enough
  proxy to guard the host, not frame-accurate). If that estimate exceeds
  `max_audio_minutes`, the request is rejected immediately with a
  plain-language 413 response, and no synthesis is attempted at all.
- If the estimate passes but the *actual* generated audio still comes out
  over the limit (the estimate can be off for unusual text/voice
  combinations), the same check runs again against the real duration as a
  safety net — this should rarely trigger.
- Either way, the error message tells the user roughly how many characters
  to cut and to try again. The frontend displays that message as-is in the
  status line — no raw errors or stack traces reach the user.
- `MAX_INPUT_CHARS` in `backend/main.py` (default 40,000) is a separate,
  even cheaper upfront sanity check that rejects obviously-too-long pastes
  before even estimating.

## Notes

- Piper (`piper-tts`) is GPL-3.0 licensed. If you're distributing this whole
  project as open source, licensing your own code under GPL-3.0 keeps things
  simple and fully compatible.
