"""Pydantic request and response models for the API.

/synthesize has no response model here: it returns raw WAV bytes, not
JSON, so there's no body shape for Pydantic to describe.
"""

from typing import Optional

from pydantic import BaseModel, model_validator


class SynthesizeRequest(BaseModel):
    text: Optional[str] = None
    url: Optional[str] = None
    voice_id: Optional[str] = None  # None or "auto" -> detect language and pick a matching voice

    @model_validator(mode="after")
    def check_one_source(self):
        if not (self.text or "").strip() and not (self.url or "").strip():
            raise ValueError("Provide either text or a url.")
        return self


class ExtractRequest(BaseModel):
    url: str


class HealthResponse(BaseModel):
    status: str
    voices_available: int


class ConfigResponse(BaseModel):
    testing: bool
    host: str
    port: int
    max_audio_minutes: float
    default_theme: str


class VoiceInfo(BaseModel):
    id: str
    language: str
    language_label: str
    label: str


class ExtractResponse(BaseModel):
    char_count: int
    title: Optional[str]

