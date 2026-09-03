"""
Read-Aloud TTS backend.

A FastAPI service that wraps the Piper TTS CLI. It accepts a block of text
over HTTP, picks a voice (explicit or auto-detected from the text's
language), and returns synthesized speech as a WAV file. Enforces a
10-minute-of-audio cap with a friendly, actionable error message.

Setup:
    pip install -r requirements.txt
    python -m piper.download_voices en_US-lessac-medium   # repeat per voice, see VOICES below
    uvicorn main:app --host 0.0.0.0 --port 8000

See README.md for deployment notes and the full list of voices to download.
"""

import subprocess
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from langdetect import DetectorFactory, LangDetectException, detect
from pydantic import BaseModel, Field

# langdetect is non-deterministic by default (random seed); pin it so the
# same text always detects the same language.
DetectorFactory.seed = 0

# --- Configuration ----------------------------------------------------------

MODELS_DIR = Path(__file__).parent / "models"
PIPER_BIN = "piper"

# Quick sanity cap on raw input size, just to reject absurd pastes before
# spending any time on synthesis. The real limit that matters to the user is
# MAX_AUDIO_SECONDS below, checked *after* synthesis against actual duration.
MAX_INPUT_CHARS = 40_000

# The actual product requirement: cap generated audio at 10 minutes.
MAX_AUDIO_SECONDS = 10 * 60

ALLOWED_ORIGINS = ["*"]  # tighten to your extension's origin before going public


@dataclass
class Voice:
    id: str              # sent by the frontend, e.g. "en_US-lessac-medium"
    filename: str         # the .onnx file inside MODELS_DIR
    language: str          # ISO 639-1 code used by langdetect, e.g. "en"
    language_label: str    # human-readable, e.g. "English"
    label: str              # human-readable voice name, e.g. "Lessac (US, medium)"

    @property
    def path(self) -> Path:
        return MODELS_DIR / self.filename


# Curated catalog. Add more entries as you download more voices with
# `python -m piper.download_voices <name>` — browse options at
# https://github.com/OHF-Voice/piper1-gpl (voice list / Hugging Face repo).
# Voices whose .onnx file isn't actually downloaded are simply hidden from
# /voices and unusable, rather than crashing the app.
VOICES = [
    Voice("en_US-lessac-medium", "en_US-lessac-medium.onnx", "en", "English", "Lessac (US, medium)"),
    Voice("en_GB-alan-medium", "en_GB-alan-medium.onnx", "en", "English", "Alan (UK, medium)"),
    Voice("de_DE-thorsten-medium", "de_DE-thorsten-medium.onnx", "de", "German", "Thorsten (medium)"),
    Voice("fr_FR-siwis-medium", "fr_FR-siwis-medium.onnx", "fr", "French", "Siwis (medium)"),
    Voice("es_ES-davefx-medium", "es_ES-davefx-medium.onnx", "es", "Spanish", "Davefx (medium)"),
    Voice("it_IT-riccardo-x_low", "it_IT-riccardo-x_low.onnx", "it", "Italian", "Riccardo (x-low)"),
    Voice("pt_BR-faber-medium", "pt_BR-faber-medium.onnx", "pt", "Portuguese", "Faber (BR, medium)"),
    Voice("nl_NL-mls-medium", "nl_NL-mls-medium.onnx", "nl", "Dutch", "MLS (medium)"),
    Voice("pl_PL-darkman-medium", "pl_PL-darkman-medium.onnx", "pl", "Polish", "Darkman (medium)"),
    Voice("hu_HU-imre-medium", "hu_HU-imre-medium.onnx", "hu", "Hungarian", "Imre (medium)"),
]

DEFAULT_FALLBACK_VOICE_ID = "en_US-lessac-medium"  # used when detection fails / no match downloaded

# --- App ----------------------------------------------------------------------

app = FastAPI(title="Read-Aloud TTS Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class SynthesizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_INPUT_CHARS)
    voice_id: Optional[str] = None  # None or "auto" -> detect language and pick a matching voice


def available_voices() -> list[Voice]:
    """Only voices whose model file is actually present on disk."""
    return [v for v in VOICES if v.path.exists()]


def resolve_voice(requested_id: Optional[str], text: str) -> tuple[Voice, Optional[str]]:
    """
    Pick the voice to use. Returns (voice, detected_language_code_or_None).

    If requested_id names a downloaded voice, use it directly (no detection).
    Otherwise, detect the text's language and pick the first downloaded voice
    that matches; fall back to DEFAULT_FALLBACK_VOICE_ID if nothing matches
    or detection fails.
    """
    downloaded = {v.id: v for v in available_voices()}
    if not downloaded:
        raise HTTPException(
            status_code=500,
            detail="No voice models are downloaded yet. See README.md to download at least one voice.",
        )

    if requested_id and requested_id != "auto" and requested_id in downloaded:
        return downloaded[requested_id], None

    try:
        detected_lang = detect(text)
    except LangDetectException:
        detected_lang = None

    if detected_lang:
        for voice in downloaded.values():
            if voice.language == detected_lang:
                return voice, detected_lang

    fallback = downloaded.get(DEFAULT_FALLBACK_VOICE_ID) or next(iter(downloaded.values()))
    return fallback, detected_lang


def wav_duration_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as wav_file:
        return wav_file.getnframes() / wav_file.getframerate()


def friendly_too_long_message(duration_seconds: float, text_char_count: int) -> str:
    minutes = duration_seconds / 60
    over_by_minutes = minutes - (MAX_AUDIO_SECONDS / 60)
    # Roughly proportional: how many fewer characters would bring it under the cap.
    cut_fraction = over_by_minutes / minutes
    suggested_chars_to_cut = int(text_char_count * cut_fraction) + 50  # small safety margin
    return (
        f"This text produces about {minutes:.1f} minutes of speech, which is "
        f"{over_by_minutes:.1f} minutes over the 10-minute limit. "
        f"Try shortening the text by roughly {suggested_chars_to_cut} characters "
        "(e.g. cut a paragraph or two) and try again."
    )


@app.get("/health")
def health():
    voices = available_voices()
    return {
        "status": "ok" if voices else "no_voices_downloaded",
        "voices_available": len(voices),
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
def synthesize(req: SynthesizeRequest):
    """Convert text to speech and return a WAV file, capped at 10 minutes of audio."""
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="No text provided.")

    voice, detected_lang = resolve_voice(req.voice_id, text)

    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        try:
            subprocess.run(
                [PIPER_BIN, "-m", str(voice.path), "-f", tmp.name],
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=180,
                check=True,
            )
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=504, detail="Speech synthesis took too long. Try a shorter text.")
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.decode(errors="ignore") if exc.stderr else "unknown error"
            raise HTTPException(status_code=500, detail=f"Speech synthesis failed: {stderr}")

        duration = wav_duration_seconds(Path(tmp.name))

        if duration > MAX_AUDIO_SECONDS:
            raise HTTPException(
                status_code=413,
                detail=friendly_too_long_message(duration, len(text)),
            )

        audio_bytes = Path(tmp.name).read_bytes()

    return Response(
        content=audio_bytes,
        media_type="audio/wav",
        headers={
            "X-Audio-Duration-Seconds": f"{duration:.2f}",
            "X-Voice-Used": voice.id,
            "X-Voice-Label": voice.label,
            "X-Detected-Language": detected_lang or "",
        },
    )
