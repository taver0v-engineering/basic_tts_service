# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 taver0v-engineering

"""Fetching a URL and pulling out its main, readable article text."""

from typing import Optional

import trafilatura
from fastapi import HTTPException


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
