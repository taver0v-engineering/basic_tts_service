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
    PORT=8000

WORKDIR /app

# Install dependencies first so this layer is cached across code changes.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Application code and the default config (config.json can still be
# overridden at runtime with a bind mount -- see compose.yaml -- without
# rebuilding the image).
COPY main.py config.json ./

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

# Plain stdlib HTTP call -- no curl/wget needed in the image just for this.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python3 -c "import os,sys,urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT','8000') + '/health', timeout=2)" || exit 1

# Always bind 0.0.0.0 inside the container -- that's what makes the
# published/mapped port reachable -- regardless of the "host" value in
# config.json (which is only used for local, non-Docker runs via
# `python main.py`, and for the frontend's default Backend URL). The port
# is read from $PORT (default 8000, see compose.yaml) so it can be changed
# without editing this file.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
