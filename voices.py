"""
Voice catalog and selection.

VOICES is the curated list of Piper voices this app knows how to offer.
available_voices() filters that down to whichever ones are actually
downloaded, and resolve_voice() picks one for a given request -- either
the one explicitly asked for, or a best guess from the text's detected
language.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from fastapi import HTTPException
from langdetect import DetectorFactory, LangDetectException, detect

from config import MODELS_DIR

# langdetect is non-deterministic by default (random seed); pin it so the
# same text always detects the same language.
DetectorFactory.seed = 0


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
