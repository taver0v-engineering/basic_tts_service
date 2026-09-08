"""
Read-Aloud TTS backend.

A FastAPI service that wraps the Piper TTS CLI. It accepts either raw text
or a URL (in which case it extracts the main article content server-side)
over HTTP, picks a voice (explicit or auto-detected from the text's
language), and returns synthesized speech as a WAV file.

This module only wires the HTTP routes together; the actual logic lives in:
    config.py   -- settings, loaded from config.json
    voices.py   -- the voice catalog and voice selection
    article.py  -- URL -> article text extraction
    speech.py   -- length estimation/limits and running Piper
    schemas.py  -- request models

Setup, configuration, and deployment notes are in README.md.

Run:
    python main.py                     # reads host/port from config.json
    # -- or --
    uvicorn main:app --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from article import extract_article
from config import ALLOWED_ORIGINS, CONFIG, DEFAULT_THEME, ENVIRONMENT, HOST, MAX_INPUT_CHARS, PORT
from schemas import SynthesizeRequest
from speech import MAX_AUDIO_SECONDS, estimate_duration_seconds, friendly_too_long_message, synthesize_with_piper
from voices import available_voices, resolve_voice

app = FastAPI(title="Read-Aloud TTS Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    voices = available_voices()
    return {
        "status": "ok" if voices else "no_voices_downloaded",
        "voices_available": len(voices),
    }


@app.get("/config")
def get_config():
    """Safe-to-expose subset of server config, used by the frontend to
    decide whether the Backend URL field should be editable and to pick a
    fallback theme when the browser can't tell us its color-scheme
    preference."""
    return {
        "environment": ENVIRONMENT,
        "host": HOST,
        "port": PORT,
        "max_audio_minutes": CONFIG["max_audio_minutes"],
        "default_theme": DEFAULT_THEME,
    }


@app.get("/voices")
def list_voices():
    """Voices the frontend can offer, grouped implicitly by language."""
    return [
        {
            "id": v.id,
            "language": v.language,
            "language_label": v.language_label,
            "label": v.label,
        }
        for v in available_voices()
    ]


@app.post("/synthesize")
async def synthesize(req: SynthesizeRequest, request: Request):
    """Convert text (or the article at a URL) to speech.

    Text whose *estimated* speaking time exceeds the configured cap is
    rejected before synthesis runs at all -- see speech.py for why. If the
    client disconnects mid-conversion (e.g. the user presses Stop), the
    underlying piper process is killed immediately rather than left to run
    to completion.
    """
    if req.url and req.url.strip():
        text, title = extract_article(req.url.strip())
        source = "link"
    else:
        text = (req.text or "").strip()
        title = None
        source = "text"

    if not text:
        raise HTTPException(status_code=400, detail="No text provided.")

    if len(text) > MAX_INPUT_CHARS:
        raise HTTPException(
            status_code=413,
            detail=f"That's {len(text)} characters — too long to process in one go. "
            f"Try a shorter article or excerpt (under {MAX_INPUT_CHARS} characters).",
        )

    estimated_duration = estimate_duration_seconds(text)
    if estimated_duration > MAX_AUDIO_SECONDS:
        raise HTTPException(
            status_code=413,
            detail=friendly_too_long_message(estimated_duration, len(text), estimated=True),
        )

    voice, detected_lang = resolve_voice(req.voice_id, text)
    result = await synthesize_with_piper(text, voice, request)

    return Response(
        content=result.audio_bytes,
        media_type="audio/wav",
        headers={
            "X-Audio-Duration-Seconds": f"{result.duration_seconds:.2f}",
            "X-Conversion-Time-Seconds": f"{result.conversion_time_seconds:.2f}",
            "X-Voice-Used": voice.id,
            "X-Voice-Label": voice.label,
            "X-Detected-Language": detected_lang or "",
            "X-Source": source,
            "X-Source-Title": title or "",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT)
