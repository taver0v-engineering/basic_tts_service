#!/usr/bin/env sh
# Download one or more Piper voices into ./models (or $MODELS_DIR).
#
# Usage:
#   ./download-voices.sh en_US-lessac-medium en_GB-alan-medium
#
# In Docker:
#   docker compose run --rm backend ./download-voices.sh en_US-lessac-medium
#
# Browse voice IDs at https://rhasspy.github.io/piper-samples/ or
# https://huggingface.co/rhasspy/piper-voices

set -e

if [ "$#" -eq 0 ]; then
  echo "Usage: $0 <voice-id> [voice-id ...]" >&2
  echo "Example: $0 en_US-lessac-medium en_GB-alan-medium" >&2
  exit 1
fi

MODELS_DIR="${MODELS_DIR:-models}"
mkdir -p "$MODELS_DIR"

for voice in "$@"; do
  echo "Downloading $voice ..."
  python -m piper.download_voices --data-dir "$MODELS_DIR" "$voice"
done

echo "Done. Downloaded voices are in $MODELS_DIR/"
echo "Remember: each new language/voice also needs a matching Voice(...) entry in main.py's VOICES list."
