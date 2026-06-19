#!/bin/bash
# make-lead-art-variants.sh — generate responsive webp variants for a blog lead image.
#
# Usage:
#   make-lead-art-variants.sh path/to/lead-art.jpg
#
# Produces, alongside the input:
#   <base>-1200.webp   (1200px wide)
#   <base>-760.webp    (760px wide)

set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <lead-art.jpg>" >&2
    exit 1
fi

SRC="$1"

if [ ! -f "$SRC" ]; then
    echo "ERROR: source image not found: $SRC" >&2
    exit 1
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
    echo "ERROR: ffmpeg is required but not found." >&2
    exit 1
fi

DIR="$(dirname "$SRC")"
BASE="$(basename "$SRC")"
STEM="${BASE%.*}"

QUALITY="${LEAD_ART_WEBP_QUALITY:-82}"

for WIDTH in 1200 760; do
    OUT="$DIR/${STEM}-${WIDTH}.webp"
    ffmpeg -y -loglevel error -i "$SRC" \
        -vf "scale=${WIDTH}:-1" \
        -c:v libwebp -quality "$QUALITY" \
        "$OUT"
    echo "wrote $OUT"
done
