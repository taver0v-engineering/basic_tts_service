# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 taver0v-engineering

"""
Configuration for the Read-Aloud TTS backend.

Settings someone might reasonably want to change live in config.json, read
once here at import time. A couple of implementation limits that aren't
meant to be user-tunable (subprocess timeout, max paste size) are defined
below as plain constants instead. See README.md for what each setting does.
"""

import json
from pathlib import Path

MODELS_DIR = Path(__file__).parent / "models"
PIPER_BIN = "piper"

# Quick sanity cap on raw input size, just to reject absurd pastes before
# spending any time on anything (extraction, estimation, synthesis).
MAX_INPUT_CHARS = 40_000

# Hard ceiling on how long piper is allowed to run for a single request,
# regardless of the estimated-duration cap below (protects against a
# pathological/slow synthesis that undershoots the char-based estimate).
SYNTHESIS_TIMEOUT_SECONDS = 180

CONFIG_PATH = Path(__file__).parent / "config.json"

DEFAULT_CONFIG = {
    # True (default) leaves the frontend's Backend URL field editable, so
    # you can point it at any backend while developing. False tells the
    # frontend to render it as fixed/uneditable (production).
    "testing": True,
    "host": "localhost",
    "port": 8000,
    # Tighten this to your actual frontend origin before going public.
    "allowed_origins": ["*"],
    # The actual product requirement: cap *estimated* speech at this many
    # minutes, checked before synthesis runs (see speech.estimate_duration_seconds).
    "max_audio_minutes": 10,
    # Rough average speaking rate used only for the pre-synthesis estimate.
    "estimated_chars_per_second": 14,
    # Fallback theme for the frontend when the browser doesn't support
    # prefers-color-scheme detection. The browser's own preference wins
    # whenever it's available.
    "default_theme": "dark",
}


def load_config() -> dict:
    """Load config.json, falling back to defaults for anything missing or
    unreadable so a bad/absent config file never prevents startup."""
    config = DEFAULT_CONFIG.copy()
    if not CONFIG_PATH.exists():
        print(f"[config] {CONFIG_PATH.name} not found next to main.py; using defaults.")
        return config

    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            user_config = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[config] Could not read {CONFIG_PATH.name} ({exc}); using defaults.")
        return config

    if not isinstance(user_config, dict):
        print(f"[config] {CONFIG_PATH.name} did not contain a JSON object; using defaults.")
        return config

    config.update({k: v for k, v in user_config.items() if k in DEFAULT_CONFIG})
    return config


CONFIG = load_config()

TESTING: bool = bool(CONFIG["testing"]) if not isinstance(CONFIG["testing"], str) else CONFIG["testing"].strip().lower() in ("1", "true", "yes", "on")
HOST: str = CONFIG["host"]
PORT: int = CONFIG["port"]
ALLOWED_ORIGINS: list[str] = CONFIG["allowed_origins"]
MAX_AUDIO_SECONDS: float = CONFIG["max_audio_minutes"] * 60
ESTIMATED_CHARS_PER_SECOND: float = CONFIG["estimated_chars_per_second"]
DEFAULT_THEME: str = CONFIG["default_theme"]
