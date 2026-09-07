"""
Read-Aloud TTS backend.

A FastAPI service that wraps the Piper TTS CLI. It accepts either raw text
or a URL (in which case it extracts the main article content server-side)
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

import trafilatura
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from langdetect import DetectorFactory, LangDetectException, detect
from pydantic import BaseModel, model_validator

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
    # English (US)
    Voice("en_US-lessac-medium", "en_US-lessac-medium.onnx", "en", "English", "Lessac (US, medium)"),
    Voice("en_US-amy-medium", "en_US-amy-medium.onnx", "en", "English", "Amy (US, medium)"),
    Voice("en_US-libritts_r-medium", "en_US-libritts_r-medium.onnx", "en", "English", "LibriTTS-R (US, medium)"),
    Voice("en_US-ryan-medium", "en_US-ryan-medium.onnx", "en", "English", "Ryan (US, medium)"),
    Voice("en_US-kristin-medium", "en_US-kristin-medium.onnx", "en", "English", "Kristin (US, medium)"),
    # English (UK)
    Voice("en_GB-alan-medium", "en_GB-alan-medium.onnx", "en", "English", "Alan (UK, medium)"),
    Voice("en_GB-vctk-medium", "en_GB-vctk-medium.onnx", "en", "English", "VCTK (UK, multi-speaker)"),
    Voice("en_GB-northern_english_male-medium", "en_GB-northern_english_male-medium.onnx", "en", "English", "Northern English Male (medium)"),
    # German
    Voice("de_DE-thorsten-medium", "de_DE-thorsten-medium.onnx", "de", "German", "Thorsten (medium)"),
    Voice("de_DE-eva_k-x_low", "de_DE-eva_k-x_low.onnx", "de", "German", "Eva K (x-low)"),
    Voice("de_DE-kerstin-low", "de_DE-kerstin-low.onnx", "de", "German", "Kerstin (low)"),
    Voice("de_DE-ramona-low", "de_DE-ramona-low.onnx", "de", "German", "Ramona (low)"),
    # French
    Voice("fr_FR-siwis-medium", "fr_FR-siwis-medium.onnx", "fr", "French", "Siwis (medium)"),
    Voice("fr_FR-gilles-low", "fr_FR-gilles-low.onnx", "fr", "French", "Gilles (low)"),
    Voice("fr_FR-upmc-medium", "fr_FR-upmc-medium.onnx", "fr", "French", "UPMC (medium)"),
    # Spanish
    Voice("es_ES-davefx-medium", "es_ES-davefx-medium.onnx", "es", "Spanish", "Davefx (medium)"),
    Voice("es_ES-carlfm-x_low", "es_ES-carlfm-x_low.onnx", "es", "Spanish", "Carlfm (x-low)"),
    Voice("es_MX-ald-medium", "es_MX-ald-medium.onnx", "es", "Spanish", "Ald (MX, medium)"),
    # Italian
    Voice("it_IT-riccardo-x_low", "it_IT-riccardo-x_low.onnx", "it", "Italian", "Riccardo (x-low)"),
    Voice("it_IT-paola-medium", "it_IT-paola-medium.onnx", "it", "Italian", "Paola (medium)"),
    # Portuguese
    Voice("pt_BR-faber-medium", "pt_BR-faber-medium.onnx", "pt", "Portuguese", "Faber (BR, medium)"),
    Voice("pt_BR-edresson-low", "pt_BR-edresson-low.onnx", "pt", "Portuguese", "Edresson (BR, low)"),
    Voice("pt_PT-tugao-medium", "pt_PT-tugao-medium.onnx", "pt", "Portuguese", "Tugão (PT, medium)"),
    # Dutch
    Voice("nl_NL-mls-medium", "nl_NL-mls-medium.onnx", "nl", "Dutch", "MLS (medium)"),
    Voice("nl_BE-nathalie-medium", "nl_BE-nathalie-medium.onnx", "nl", "Dutch", "Nathalie (BE, medium)"),
    # Polish
    Voice("pl_PL-darkman-medium", "pl_PL-darkman-medium.onnx", "pl", "Polish", "Darkman (medium)"),
    Voice("pl_PL-gosia-medium", "pl_PL-gosia-medium.onnx", "pl", "Polish", "Gosia (medium)"),
    # Hungarian
    Voice("hu_HU-imre-medium", "hu_HU-imre-medium.onnx", "hu", "Hungarian", "Imre (medium)"),
    Voice("hu_HU-anna-medium", "hu_HU-anna-medium.onnx", "hu", "Hungarian", "Anna (medium)"),
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
    text: Optional[str] = None
    url: Optional[str] = None
    voice_id: Optional[str] = None  # None or "auto" -> detect language and pick a matching voice

    @model_validator(mode="after")
    def check_one_source(self):
        if not (self.text or "").strip() and not (self.url or "").strip():
            raise ValueError("Provide either text or a url.")
        return self


def extract_article(url: str) -> tuple[str, Optional[str]]:
    """Fetch a URL and pull out the main article text (title, if found).

    Uses trafilatura.extract() for the text (a plain string across all
    trafilatura versions) and extract_metadata() for the title, rather than
    bare_extraction()'s return value, whose type (dict vs. Document object)
    has changed across trafilatura releases.
    """
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        raise HTTPException(
            status_code=400,
            detail="Could not fetch that link. Check the URL is correct and publicly accessible.",
        )

    text = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
    if not text or not text.strip():
        raise HTTPException(
            status_code=422,
            detail="Could not find readable article content at that link. Try pasting the text directly instead.",
        )

    title = None
    try:
        metadata = trafilatura.extract_metadata(downloaded)
        if metadata is not None:
            title = getattr(metadata, "title", None) or (
                metadata.get("title") if hasattr(metadata, "get") else None
            )
    except Exception:
        title = None  # title is a nice-to-have; never fail the request over it

    return text.strip(), title


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
    """Convert text (or the article at a URL) to speech, capped at 10 minutes of audio."""
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
            "X-Source": source,
            "X-Source-Title": title or "",
        },
    )
