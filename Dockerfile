# syntax=docker/dockerfile:1

# --- Read Aloud backend image -----------------------------------------------
#
# Base: the official Debian-based "slim" Python image. Debian is a fully
# free (DFSG) distribution, "slim" strips it down to what's needed to run
# Python, and its glibc base means the prebuilt wheels for onnxruntime
# (Piper's inference engine) and lxml (used by trafilatura) install as
# plain binary wheels -- no compiler, no extra system packages. An
# Alpine/musl base would be smaller on paper but currently forces those two
# packages to build from source (slow, and pulls in a full C/C++ toolchain
# anyway), so slim-on-glibc ends up simpler and often smaller in practice.
FROM python:3.12-slim-bookworm

# Don't buffer stdout/stderr (logs show up immediately via `docker logs`),
# don't write .pyc files into the image layer, and don't cache pip's
# downloads (keeps the image smaller).
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000 \
    MODELS_DIR=models

WORKDIR /app

# Install dependencies first so this layer is cached across code changes.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Application code and the default config (config.json can still be
# overridden at runtime with a bind mount -- see compose.yaml -- without
# rebuilding the image).
COPY article.py config.py main.py schemas.py speech.py voices.py download-voices.sh config.json ./

RUN chmod +x /app/download-voices.sh

# Voice models (.onnx / .onnx.json) are downloaded separately -- see
# README.md -- and are expected to live here. This is mounted as a volume
# in compose.yaml so models persist across rebuilds instead of bloating the
# image; the empty directory just makes the container work before any
# volume is attached.
RUN mkdir -p /app/models

# Run as a non-root user.
RUN useradd --create-home --uid 1000 readaloud \
    && chown -R readaloud:readaloud /app
USER readaloud

EXPOSE 8000

# No HEALTHCHECK instruction here on purpose. Baking one into the image
# only works with Docker's own image manifest format -- Podman defaults to
# building OCI-format images, which have no slot for image-level
# HEALTHCHECK metadata at all (Podman just warns and silently drops it
# during build: "HEALTHCHECK is not supported for OCI image format").
# The equivalent check is defined instead in compose.yaml's `healthcheck:`
# key, which both `docker compose` and Podman apply at container *run*
# time (translated to plain --health-cmd/--health-interval flags) rather
# than needing to be embedded in the image -- one definition, no warning,
# works under both tools.

# Always bind 0.0.0.0 inside the container -- that's what makes the
# published/mapped port reachable -- regardless of the "host" value in
# config.json (which is only used for local, non-Docker runs via
# `python main.py`, and for the frontend's default Backend URL). The port
# is read from $PORT (default 8000, see compose.yaml) so it can be changed
# without editing this file.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]