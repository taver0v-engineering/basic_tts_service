"""
Read-Aloud TTS backend.

A minimal FastAPI service that wraps the Piper TTS CLI. It accepts a block
of text over HTTP and returns synthesized speech as a WAV file.

Setup:
    pip install -r requirements.txt
    python -m piper.download_voices en_US-lessac-medium   # downloads the voice model
    uvicorn main:app --host 0.0.0.0 --port 8000

See README.md for deployment notes (Hugging Face Spaces, Render, Oracle Cloud, etc).
"""

import subprocess
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

# --- Configuration ------------------------------------------------------

# Where the downloaded Piper voice model (.onnx) lives. Change the name if
# you download a different voice with `python -m piper.download_voices`.
MODEL_PATH = Path(__file__).parent / "models" / "en_US-lessac-medium.onnx"

# Name of the piper executable. `pip install piper-tts` puts this on PATH.
PIPER_BIN = "piper"

# Simple guardrail so one oversized request can't tie up the server.
# ~20,000 characters covers a very long article with headroom.
MAX_CHARS = 20_000

# Restrict this to your extension's actual origin before going public, e.g.
# ["chrome-extension://your-extension-id"]. "*" is fine for local testing.
ALLOWED_ORIGINS = ["*"]

# --- App ------------------------------------------------------------------

app = FastAPI(title="Read-Aloud TTS Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class SynthesizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_CHARS)


@app.get("/health")
def health():
    """Quick check that the service is up and the voice model is present."""
    return {
        "status": "ok" if MODEL_PATH.exists() else "missing_model",
        "model_path": str(MODEL_PATH),
    }


@app.post("/synthesize")
def synthesize(req: SynthesizeRequest):
    """Convert text to speech and return a WAV file."""
    if not MODEL_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Voice model not found at {MODEL_PATH}. "
            "Run `python -m piper.download_voices en_US-lessac-medium` first.",
        )

    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="No text provided.")

    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        try:
            subprocess.run(
                [PIPER_BIN, "-m", str(MODEL_PATH), "-f", tmp.name],
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=120,
                check=True,
            )
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=504, detail="Speech synthesis took too long.")
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.decode(errors="ignore") if exc.stderr else "unknown error"
            raise HTTPException(status_code=500, detail=f"Piper failed: {stderr}")

        audio_bytes = Path(tmp.name).read_bytes()

    return Response(content=audio_bytes, media_type="audio/wav")
