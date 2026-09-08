"""
Running Piper and keeping generated speech within the configured length cap.

The cap is enforced in two passes: a cheap *estimate* before synthesis runs
(the actual point -- protect the host from long-running conversions before
spending any CPU on them, not just limit output length), and a safety-net
check against the *real* duration afterwards, in case the estimate was off
for an unusual text/voice combination.
"""

import asyncio
import tempfile
import time
import wave
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, Request

from config import ESTIMATED_CHARS_PER_SECOND, MAX_AUDIO_SECONDS, PIPER_BIN, SYNTHESIS_TIMEOUT_SECONDS
from voices import Voice


@dataclass
class SynthesisResult:
    audio_bytes: bytes
    duration_seconds: float
    conversion_time_seconds: float


def estimate_duration_seconds(text: str) -> float:
    """
    Rough estimate of how many seconds of audio this text will produce.

    This runs *before* synthesis so obviously-too-long requests can be
    rejected without spending time on the comparatively expensive piper
    subprocess. It's deliberately simple (a configurable average
    characters-per-second speaking rate) rather than per-voice/per-language
    accurate -- it only needs to be a good enough proxy to guard the host.
    """
    if ESTIMATED_CHARS_PER_SECOND <= 0:
        return 0.0
    return len(text) / ESTIMATED_CHARS_PER_SECOND


def friendly_too_long_message(duration_seconds: float, text_char_count: int, estimated: bool) -> str:
    minutes = duration_seconds / 60
    limit_minutes = MAX_AUDIO_SECONDS / 60
    over_by_minutes = minutes - limit_minutes
    # Roughly proportional: how many fewer characters would bring it under the cap.
    cut_fraction = over_by_minutes / minutes if minutes else 0
    suggested_chars_to_cut = int(text_char_count * cut_fraction) + 50  # small safety margin
    lead = (
        f"This text is estimated to produce about {minutes:.1f} minutes of speech"
        if estimated
        else f"This text produced about {minutes:.1f} minutes of speech"
    )
    return (
        f"{lead}, which is {over_by_minutes:.1f} minutes over the {limit_minutes:.0f}-minute limit. "
        f"Try shortening the text by roughly {suggested_chars_to_cut} characters "
        "(e.g. cut a paragraph or two) and try again."
    )


def _wav_duration_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as wav_file:
        return wav_file.getnframes() / wav_file.getframerate()


async def synthesize_with_piper(text: str, voice: Voice, request: Request) -> SynthesisResult:
    """
    Run Piper on `text` with `voice` and return the resulting audio.

    Raises HTTPException if: the client disconnects mid-conversion (499,
    the underlying piper process is killed immediately rather than left to
    finish), synthesis takes longer than SYNTHESIS_TIMEOUT_SECONDS (504),
    piper exits with an error (500), or the actual output still comes out
    over the length cap despite passing the pre-synthesis estimate (413).
    """
    start_time = time.monotonic()

    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        proc = await asyncio.create_subprocess_exec(
            PIPER_BIN,
            "-m",
            str(voice.path),
            "-f",
            tmp.name,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        proc.stdin.write(text.encode("utf-8"))
        await proc.stdin.drain()
        proc.stdin.close()

        await _wait_for_piper(proc, request)

        if proc.returncode != 0:
            stderr = await proc.stderr.read()
            raise HTTPException(
                status_code=500,
                detail=f"Speech synthesis failed: {stderr.decode(errors='ignore') if stderr else 'unknown error'}",
            )

        conversion_time = time.monotonic() - start_time
        duration = _wav_duration_seconds(Path(tmp.name))

        if duration > MAX_AUDIO_SECONDS:
            raise HTTPException(
                status_code=413,
                detail=friendly_too_long_message(duration, len(text), estimated=False),
            )

        return SynthesisResult(
            audio_bytes=Path(tmp.name).read_bytes(),
            duration_seconds=duration,
            conversion_time_seconds=conversion_time,
        )


async def _wait_for_piper(proc: asyncio.subprocess.Process, request: Request) -> None:
    """Poll until piper exits, killing it early (and raising) if the client
    disconnects or the hard timeout is hit."""
    elapsed = 0.0
    poll_interval = 0.25
    while proc.returncode is None:
        if await request.is_disconnected():
            proc.kill()
            await proc.wait()
            raise HTTPException(status_code=499, detail="Conversion cancelled.")
        if elapsed >= SYNTHESIS_TIMEOUT_SECONDS:
            proc.kill()
            await proc.wait()
            raise HTTPException(status_code=504, detail="Speech synthesis took too long. Try a shorter text.")
        try:
            await asyncio.wait_for(proc.wait(), timeout=poll_interval)
        except asyncio.TimeoutError:
            elapsed += poll_interval
