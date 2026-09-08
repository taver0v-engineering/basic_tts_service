"""Pydantic request models for the API."""

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
