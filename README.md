# Read Aloud

A minimal, free, self-hosted text-to-speech reader:
- **Backend** (`backend/`): FastAPI service that wraps [Piper TTS](https://github.com/OHF-Voice/piper1-gpl) (CPU-only, no GPU needed). Accepts either raw text or a URL (extracts the article server-side), supports multiple languages/voices, auto-detects the text's language when you don't pick one, and rejects text whose *estimated* speaking time is over a configurable cap (default 10 minutes) before running the (comparatively expensive) synthesis step. All of this is controlled by `backend/config.json`, read once at startup. Runs in a venv or as a Docker container (see "Running with Docker" below).
- **Frontend** (`frontend/index.html`): paste an article *and/or* a link — whichever field you click into (or type into) becomes the "active" one Convert will use, shown clearly on each field, so you never have to delete anything just to switch. Pick a language/voice (or leave on Auto — resets automatically whenever the active field's content changes), press **Convert** (or **Stop** to cancel mid-conversion), then once it's ready press **Play** (same button doubles as Pause) — plus Restart, skip ±10s/±30s, and a draggable seek bar to jump anywhere in the audio. A status indicator always shows whether conversion is in progress (with a live timer), ready (with the total conversion time), playing, cancelled, or failed. A theme toggle in the header switches between dark (default) and light; it follows your browser/OS preference automatically until you override it.
 

## Table of Contents

- [Read Aloud](#read-aloud)
  - [Table of Contents](#table-of-contents)
  - [1. Run the backend locally](#1-run-the-backend-locally)
  - [2. Open the frontend](#2-open-the-frontend)
  - [3. Running with Docker (or Podman)](#3-running-with-docker-or-podman)
  - [Configuration (`backend/config.json`)](#configuration-backendconfigjson)
  - [How language/voice selection works](#how-languagevoice-selection-works)
  - [Converting from a link instead of pasted text](#converting-from-a-link-instead-of-pasted-text)
  - [Switching between text and a link](#switching-between-text-and-a-link)
  - [Frontend playback controls](#frontend-playback-controls)
  - [Theme](#theme)
  - [The speaking-time limit](#the-speaking-time-limit)
  - [Notes](#notes)
  - [Licensing](#licensing)
    - [⚠️ Voice models are licensed separately — read this before commercial use](#️-voice-models-are-licensed-separately--read-this-before-commercial-use)
    - [Voice license summary for the voices shipped in `voices.py`](#voice-license-summary-for-the-voices-shipped-in-voicespy)
    - [If you just want a commercially safe set](#if-you-just-want-a-commercially-safe-set)
    - [Contributing](#contributing)
  - [Licensing](#licensing-1)
    - [⚠️ Voice models are licensed separately — read this before commercial use](#️-voice-models-are-licensed-separately--read-this-before-commercial-use-1)
    - [Voice license summary for the voices shipped in `voices.py`](#voice-license-summary-for-the-voices-shipped-in-voicespy-1)
    - [If you just want a commercially safe set](#if-you-just-want-a-commercially-safe-set-1)
    - [Contributing](#contributing-1)


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
# in backend/voices.py if you download these):
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
entry added to the `VOICES` list in `backend/voices.py` (a handful of common
ones are already there) — copy the pattern for any extra voice/language you add.

## 2. Open the frontend

Just open `frontend/index.html` in a browser (double-click it, or serve it with
any static file server). By default it points at `http://localhost:8000`
(matching `config.json`'s default `host`/`port`) — change the "Backend URL"
field at the bottom of the page once you deploy the backend somewhere public.
That field is only editable when the backend's `environment` is `"test"`; in
`"production"` it's fixed and shown read-only, based on what `GET /config`
reports.

## 3. Running with Docker (or Podman)

This repo includes a `Dockerfile`, `compose.yaml`, `.dockerignore`, and
`.env.example` for the backend, if you'd rather run it as a container than
in a venv. Everything below works the same under Docker and Podman --
swap the `docker` binary for `podman` in any command that isn't
`docker compose`, and use `podman compose` in place of `docker compose`.
The image is built on Debian's official `python:3.12-slim-bookworm` —
Debian is a fully free (DFSG) distribution, "slim" keeps the image small,
and its glibc base means Piper's `onnxruntime` dependency and
trafilatura's `lxml` dependency install as plain prebuilt wheels (no
compiler needed, unlike an Alpine/musl base, which currently forces both
to build from source).

Modify rights for these files on the host, before containerazition:
```bash
chmod 644 config.json      # rw-r--r--  (owner write, everyone read)
chmod 644 index.html
chmod 644 favicon.svg
chmod 755 download-voices.sh   # rwxr-xr-x
```

```bash
# Build the image and start the backend
docker compose up -d --build

# Download at least one voice into the models/ volume (repeat per voice,
# same IDs as the bare-metal instructions above). This calls the built
# image directly with `run` rather than `docker compose run` -- see the
# Podman note below for why -- but works identically under Docker.
docker run --rm -v ./models:/app/models:Z read-aloud-backend \
  python -m piper.download_voices --data-dir models en_US-lessac-medium

# -- or, using the bundled helper script for several at once --
docker run --rm -v ./models:/app/models:Z read-aloud-backend \
  ./download-voices.sh en_US-lessac-medium en_GB-alan-medium

# Pick up newly downloaded voices (piper.download_voices doesn't require a
# restart to be seen by /voices, but it's a good habit to check /health)
curl http://localhost:8000/health
```

> **Podman note:** the voice-download step above intentionally uses
> `docker run`/`podman run` directly against the already-built
> `read-aloud-backend` image, instead of `docker compose run --rm backend
> ...`. Podman's Compose emulation shells out to the classic Python
> `docker-compose` tool for `run`, which still issues legacy container
> `--link` flags for the service; Podman rejects these with `bad
> parameter: link is not supported`. Calling the image directly with
> plain `run` sidesteps that path entirely and is otherwise the same
> command either way. Only the long-running `backend`/`frontend` services
> are started through `compose up`, which doesn't hit this issue. The
> `:Z` suffix on the volume mount is an SELinux-relabeling option
> supported by both Docker and Podman; it's a no-op on non-SELinux hosts.

A few things specific to the containerized setup:

- **Networking**: the container always binds `0.0.0.0` internally regardless
  of `host` in `config.json` — that's what makes the port mapping in
  `compose.yaml` work. `config.json`'s `host`/`port` fields still matter for
  local (non-Docker) `python main.py` runs and for the frontend's default
  Backend URL, but don't need to match the container's internal bind
  address.
- **Port**: controlled by the `PORT` environment variable (default `8000`),
  read by both the `ports` mapping and the container's `CMD` in
  `compose.yaml`. Copy `.env.example` to `.env` and change `PORT` there to
  use a different port — no need to edit `compose.yaml` or the `Dockerfile`.
- **Models**: `./models` is bind-mounted into the container, so downloaded
  voices persist across rebuilds/restarts instead of bloating the image.
  Each voice you download still needs a matching `Voice(...)` entry in
  `voices.py`'s `VOICES` list (same as the bare-metal setup) — edit
  `voices.py` and re-run `docker compose up -d --build` to pick it up.
- **Config**: `config.json` is bind-mounted read-only into the container, so
  you can edit `environment`, `allowed_origins`, `max_audio_minutes`, etc.
  and just `docker compose restart backend` — no rebuild needed.
- **Frontend**: `compose.yaml` includes an optional `frontend` service that
  serves `index.html` via stock `nginx:1.27-alpine` (no custom image, just a
  bind mount) at `http://localhost:8080`. Remove that service if you'd
  rather open `index.html` directly or host it elsewhere. Either way, if
  you set `"environment": "production"`, the frontend's Backend URL field
  becomes fixed at whatever default is baked into `index.html` — edit that
  default (the `<input id="backendUrl">` element's `value`) to your real,
  publicly reachable backend address *before* deploying it that way, since
  the field can no longer be corrected from the browser.
- **Health**: the backend's healthcheck is defined in `compose.yaml` (a
  `healthcheck:` block calling `/health` with Python's standard library —
  no `curl`/`wget` needed), visible via `docker ps`/`podman ps` or
  `docker inspect`/`podman inspect`. It's defined at the Compose level
  rather than as a Dockerfile `HEALTHCHECK` instruction on purpose: Podman
  builds images in OCI format by default, which has no slot for an
  image-level `HEALTHCHECK` at all (Podman just warns and drops it during
  build) — defining it in `compose.yaml` instead applies it at
  container-run time, which both tools support identically.

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
  back to `DEFAULT_FALLBACK_VOICE_ID` in `backend/voices.py` (English by default).
- Picking a specific voice from the dropdown skips detection entirely and
  uses exactly that voice.
- Add more languages by downloading more voices (see above) and adding a
  matching `Voice(...)` entry to the `VOICES` list in `backend/voices.py`.

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
- While you're typing/pasting a link (before pressing Convert), the frontend
  calls `POST /extract` — the same extraction step, without synthesizing
  anything — so the character count shown under the link field reflects the
  article's actual length rather than the URL string's length. This is
  debounced to fire shortly after you stop typing, not on every keystroke.

## Switching between text and a link

- Both fields can hold content at the same time — they're no longer
  mutually exclusive. Instead, whichever one you click into (or start
  typing/pasting into) becomes the **active** field, and that's what
  **Convert** will use; the other one stays fully editable (so you can
  prep both in advance) but is visually dimmed and tagged **Inactive** to
  make it obvious it'll be ignored. Switching is just a click — no need to
  delete anything.
- Whenever the active field's content changes, the Language and Voice
  pickers reset back to **Auto**, since a voice/language chosen for one
  piece of text may not fit newly pasted content.
- The indicator below the fields (e.g. "Active: Text — this is what
  Convert will use.") is dim and neutral by default, including right after
  startup, and only picks up an accent color once the active field actually
  has content ready to convert — so an empty state never reads like
  something's wrong.

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
- `MAX_INPUT_CHARS` in `backend/config.py` (default 40,000) is a separate,
  even cheaper upfront sanity check that rejects obviously-too-long pastes
  before even estimating.

## Notes

- `requirements.txt` uses unpinned/minimum-version constraints rather than
  exact `==` pins, so `pip install -r requirements.txt` picks up the latest
  compatible release of each package at install time. That's convenient for
  staying current with upstream fixes, but it does mean the venv setup and
  the Docker image are guaranteed to install byte-identical dependency
  versions on two different days. If you need reproducible installs (e.g.
  for a production deployment), generate a lockfile once you have a known-
  good set of versions — `pip freeze > constraints.txt` and installing with
  `pip install -r requirements.txt -c constraints.txt` is the simplest way
  to do that without changing `requirements.txt` itself.
- Piper (`piper-tts`) is GPL-3.0 licensed. If you're distributing this whole
  project as open source, licensing your own code under GPL-3.0 keeps things
  simple and fully compatible.
- `frontend/favicon.svg` is a plain, hand-written SVG (no build step) linked
  from `index.html`'s `<head>`. Modern Chrome, Firefox, and Safari all
  support SVG favicons directly; if you need to support a browser that
  doesn't, rasterize it once (e.g. `rsvg-convert favicon.svg -o favicon.png`
  or any online SVG-to-PNG/ICO converter) and add a second `<link rel="icon">`
  pointing at that file as a fallback.
- **Custom response headers are ASCII-encoded by convention.** Any header
  value derived from user input or library metadata (article titles, voice
  labels) can contain arbitrary Unicode, which Starlette rejects at
  response time (`UnicodeEncodeError: 'latin-1' codec can't encode ...`)
  *after* synthesis has already run. To prevent that class of bug, every
  custom header on a response is built via `safe_headers()` in
  `backend/http_headers.py`, which percent-encodes values to pure ASCII;
  the frontend decodes each one with `decodeURIComponent` via its
  `readHeader()` helper. **Add new headers by extending the dict passed to
  `safe_headers()`, not by setting them elsewhere** — that's what keeps the
  guarantee total rather than per-call-site.

## Licensing

This project is released under the **GNU General Public License v3.0 (GPL-3.0)**. See the [`LICENSE`](LICENSE) file for the full text.

**What that means in practice:** you are free to use, study, modify, and redistribute this software — including for commercial purposes and including as part of a paid product or service. The condition is that if you *distribute* the software (or a modified version of it) to others, you must do so under the same GPL-3.0 terms and make the complete corresponding source code available. Running it privately, or offering it as a hosted service without shipping the code to users, does not by itself trigger that obligation. This is the same copyleft model used by Linux, WordPress, and countless other projects, and it is fully compatible with commercial use.

This project depends on [Piper TTS](https://github.com/OHF-Voice/piper1-gpl), which is itself GPL-3.0 licensed. That is the main reason this project is GPL-3.0 rather than MIT/Apache — we cannot offer more permissive terms than the engine we build on.

A full list of third-party dependencies and their licenses is in [`LICENSE-THIRD-PARTY.md`](LICENSE-THIRD-PARTY.md). Full license texts are in the [`LICENSES/`](LICENSES/) directory.

### ⚠️ Voice models are licensed separately — read this before commercial use

**This project does not bundle, ship, or redistribute any voice models.** You download them yourself with `python -m piper.download_voices <name>` (or the equivalent Docker command). This is deliberate, and it matters:

- **The Piper *engine*** is GPL-3.0.
- **The Piper *voice models*** are *separate works* with **their own licenses**, and those licenses are **not uniform**. They range from public-domain (CC0), through permissive attribution licenses (CC-BY, MIT, Apache-2.0), to **non-commercial licenses (CC-BY-NC, CC-BY-NC-SA) that forbid commercial use entirely**.

**You are responsible for checking the license of each voice you download before using it** — especially if you intend to use this app commercially, ship it inside a product, or offer it as a paid service. Downloading a voice and using it does not grant you any rights the voice's own license withholds.

The authoritative source for a given voice's license is its `MODEL_CARD` file in the upstream voices repository:

> **https://huggingface.co/rhasspy/piper-voices**

Each voice folder there contains a `MODEL_CARD` file that lists the license and the dataset it was trained on. That is the source of truth; anything in this project (including the table below) is a convenience summary, not a legal statement.

### Voice license summary for the voices shipped in `voices.py`

The table below summarizes what we currently believe about each voice's license. **It is provided as a starting point only, and may become out of date as upstream voices are re-licensed, renamed, or replaced.** Verify against the `MODEL_CARD` before relying on it, particularly for commercial use.

| Voice ID | Language | License | Commercial use |
| :--- | :--- | :--- | :--- |
| `en_US-lessac-medium` | English (US) | MIT | ✅ Yes |
| `en_US-amy-medium` | English (US) | Apache-2.0 | ✅ Yes |
| `en_US-libritts_r-medium` | English (US) | CC-BY-4.0 | ✅ Yes (with attribution) |
| `en_US-ryan-medium` | English (US) | CC-BY-4.0 | ✅ Yes (with attribution) |
| `en_US-kristin-medium` | English (US) | CC-BY-4.0 | ✅ Yes (with attribution) |
| `en_GB-alan-medium` | English (UK) | CC-BY-4.0 | ✅ Yes (with attribution) |
| `en_GB-vctk-medium` | English (UK) | CC-BY-4.0 | ✅ Yes (with attribution) |
| `en_GB-northern_english_male-medium` | English (UK) | CC-BY-4.0 | ✅ Yes (with attribution) |
| `de_DE-thorsten-medium` | German | CC0-1.0 | ✅ Yes |
| `de_DE-eva_k-x_low` | German | BSD-style (M-AILABS) | ✅ Yes |
| `de_DE-kerstin-low` | German | CC0-1.0 | ✅ Yes |
| `de_DE-ramona-low` | German | BSD-style (M-AILABS) | ✅ Yes |
| `fr_FR-siwis-medium` | French | CC-BY-4.0 | ✅ Yes (with attribution) |
| `fr_FR-gilles-low` | French | CC0-1.0 | ✅ Yes |
| `fr_FR-upmc-medium` | French | CC-BY-4.0 | ✅ Yes (with attribution) |
| `es_ES-davefx-medium` | Spanish | CC0-1.0 | ✅ Yes |
| `es_ES-carlfm-x_low` | Spanish | CC0-1.0 | ✅ Yes |
| `es_MX-ald-medium` | Spanish (MX) | CC-BY-4.0 | ✅ Yes (with attribution) |
| `it_IT-riccardo-x_low` | Italian | MIT | ✅ Yes |
| `it_IT-paola-medium` | Italian | CC-BY-4.0 | ✅ Yes (with attribution) |
| `pt_BR-faber-medium` | Portuguese (BR) | CC0-1.0 | ✅ Yes |
| `pt_BR-edresson-low` | Portuguese (BR) | CC-BY-4.0 | ✅ Yes (with attribution) |
| `pt_PT-tugao-medium` | Portuguese (PT) | CC-BY-4.0 | ✅ Yes (with attribution) |
| `nl_NL-mls-medium` | Dutch | CC-BY-4.0 | ✅ Yes (with attribution) |
| `nl_BE-nathalie-medium` | Dutch (BE) | CC-BY-4.0 | ✅ Yes (with attribution) |
| `pl_PL-darkman-medium` | Polish | CC0-1.0 | ✅ Yes |
| `pl_PL-gosia-medium` | Polish | CC0-1.0 | ✅ Yes |
| `hu_HU-imre-medium` | Hungarian | CC0-1.0 | ✅ Yes |
| `hu_HU-anna-medium` | Hungarian | CC0-1.0 | ✅ Yes |

**Voices to avoid if you need commercial use:** any voice whose `MODEL_CARD` says `CC-BY-NC`, `CC-BY-NC-SA`, `CC-BY-NC-ND`, or similar. None of the voices listed in `voices.py` above fall into this category as of this writing, but the upstream catalog does contain such voices — check before adding new ones.

### If you just want a commercially safe set

If you don't want to audit voice licenses one by one, stick to the CC0 and MIT voices in the table above (e.g. `en_US-lessac-medium`, `de_DE-thorsten-medium`, `fr_FR-gilles-low`, `es_ES-davefx-medium`, `it_IT-riccardo-x_low`, `pl_PL-darkman-medium`, `hu_HU-imre-medium`). These have no attribution requirement and no commercial restriction. The CC-BY voices are also fine for commercial use, but require you to preserve attribution to the voice's original creator somewhere in your product or distribution.

### Contributing

By submitting a pull request, you agree that your contribution may be distributed under the project's GPL-3.0 license. If you add a new voice to `voices.py`, please also add its license to the table above (and to `LICENSE-THIRD-PARTY.md`) so the project's licensing documentation stays accurate.

## Licensing

This project is released under the **GNU General Public License v3.0 (GPL-3.0)**. See the [`LICENSE`](LICENSE) file for the full text.

**What that means in practice:** you are free to use, study, modify, and redistribute this software — including for commercial purposes and including as part of a paid product or service. The condition is that if you *distribute* the software (or a modified version of it) to others, you must do so under the same GPL-3.0 terms and make the complete corresponding source code available. Running it privately, or offering it as a hosted service without shipping the code to users, does not by itself trigger that obligation. This is the same copyleft model used by Linux, WordPress, and countless other projects, and it is fully compatible with commercial use.

This project depends on [Piper TTS](https://github.com/OHF-Voice/piper1-gpl), which is itself GPL-3.0 licensed. That is the main reason this project is GPL-3.0 rather than MIT/Apache — we cannot offer more permissive terms than the engine we build on.

A full list of third-party dependencies and their licenses is in [`LICENSE-THIRD-PARTY.md`](LICENSE-THIRD-PARTY.md). Full license texts are in the [`LICENSES/`](LICENSES/) directory.

### ⚠️ Voice models are licensed separately — read this before commercial use

**This project does not bundle, ship, or redistribute any voice models.** You download them yourself with `python -m piper.download_voices <name>` (or the equivalent Docker command). This is deliberate, and it matters:

- **The Piper *engine*** is GPL-3.0.
- **The Piper *voice models*** are *separate works* with **their own licenses**, and those licenses are **not uniform**. They range from public-domain (CC0), through permissive attribution licenses (CC-BY, MIT, Apache-2.0), to **non-commercial licenses (CC-BY-NC, CC-BY-NC-SA) that forbid commercial use entirely**.

**You are responsible for checking the license of each voice you download before using it** — especially if you intend to use this app commercially, ship it inside a product, or offer it as a paid service. Downloading a voice and using it does not grant you any rights the voice's own license withholds.

The authoritative source for a given voice's license is its `MODEL_CARD` file in the upstream voices repository:

> **https://huggingface.co/rhasspy/piper-voices**

Each voice folder there contains a `MODEL_CARD` file that lists the license and the dataset it was trained on. That is the source of truth; anything in this project (including the table below) is a convenience summary, not a legal statement.

### Voice license summary for the voices shipped in `voices.py`

The table below summarizes what we currently believe about each voice's license. **It is provided as a starting point only, and may become out of date as upstream voices are re-licensed, renamed, or replaced.** Verify against the `MODEL_CARD` before relying on it, particularly for commercial use.

| Voice ID | Language | License | Commercial use |
| :--- | :--- | :--- | :--- |
| `en_US-lessac-medium` | English (US) | MIT | ✅ Yes |
| `en_US-amy-medium` | English (US) | Apache-2.0 | ✅ Yes |
| `en_US-libritts_r-medium` | English (US) | CC-BY-4.0 | ✅ Yes (with attribution) |
| `en_US-ryan-medium` | English (US) | CC-BY-4.0 | ✅ Yes (with attribution) |
| `en_US-kristin-medium` | English (US) | CC-BY-4.0 | ✅ Yes (with attribution) |
| `en_GB-alan-medium` | English (UK) | CC-BY-4.0 | ✅ Yes (with attribution) |
| `en_GB-vctk-medium` | English (UK) | CC-BY-4.0 | ✅ Yes (with attribution) |
| `en_GB-northern_english_male-medium` | English (UK) | CC-BY-4.0 | ✅ Yes (with attribution) |
| `de_DE-thorsten-medium` | German | CC0-1.0 | ✅ Yes |
| `de_DE-eva_k-x_low` | German | BSD-style (M-AILABS) | ✅ Yes |
| `de_DE-kerstin-low` | German | CC0-1.0 | ✅ Yes |
| `de_DE-ramona-low` | German | BSD-style (M-AILABS) | ✅ Yes |
| `fr_FR-siwis-medium` | French | CC-BY-4.0 | ✅ Yes (with attribution) |
| `fr_FR-gilles-low` | French | CC0-1.0 | ✅ Yes |
| `fr_FR-upmc-medium` | French | CC-BY-4.0 | ✅ Yes (with attribution) |
| `es_ES-davefx-medium` | Spanish | CC0-1.0 | ✅ Yes |
| `es_ES-carlfm-x_low` | Spanish | CC0-1.0 | ✅ Yes |
| `es_MX-ald-medium` | Spanish (MX) | CC-BY-4.0 | ✅ Yes (with attribution) |
| `it_IT-riccardo-x_low` | Italian | MIT | ✅ Yes |
| `it_IT-paola-medium` | Italian | CC-BY-4.0 | ✅ Yes (with attribution) |
| `pt_BR-faber-medium` | Portuguese (BR) | CC0-1.0 | ✅ Yes |
| `pt_BR-edresson-low` | Portuguese (BR) | CC-BY-4.0 | ✅ Yes (with attribution) |
| `pt_PT-tugao-medium` | Portuguese (PT) | CC-BY-4.0 | ✅ Yes (with attribution) |
| `nl_NL-mls-medium` | Dutch | CC-BY-4.0 | ✅ Yes (with attribution) |
| `nl_BE-nathalie-medium` | Dutch (BE) | CC-BY-4.0 | ✅ Yes (with attribution) |
| `pl_PL-darkman-medium` | Polish | CC0-1.0 | ✅ Yes |
| `pl_PL-gosia-medium` | Polish | CC0-1.0 | ✅ Yes |
| `hu_HU-imre-medium` | Hungarian | CC0-1.0 | ✅ Yes |
| `hu_HU-anna-medium` | Hungarian | CC0-1.0 | ✅ Yes |

**Voices to avoid if you need commercial use:** any voice whose `MODEL_CARD` says `CC-BY-NC`, `CC-BY-NC-SA`, `CC-BY-NC-ND`, or similar. None of the voices listed in `voices.py` above fall into this category as of this writing, but the upstream catalog does contain such voices — check before adding new ones.

### If you just want a commercially safe set

If you don't want to audit voice licenses one by one, stick to the CC0 and MIT voices in the table above (e.g. `en_US-lessac-medium`, `de_DE-thorsten-medium`, `fr_FR-gilles-low`, `es_ES-davefx-medium`, `it_IT-riccardo-x_low`, `pl_PL-darkman-medium`, `hu_HU-imre-medium`). These have no attribution requirement and no commercial restriction. The CC-BY voices are also fine for commercial use, but require you to preserve attribution to the voice's original creator somewhere in your product or distribution.

### Contributing

By submitting a pull request, you agree that your contribution may be distributed under the project's GPL-3.0 license. If you add a new voice to `voices.py`, please also add its license to the table above (and to `LICENSE-THIRD-PARTY.md`) so the project's licensing documentation stays accurate.
