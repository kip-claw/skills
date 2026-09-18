#!/usr/bin/env bash
# Convenience wrapper for the milkdrop OpenClaw skill.
#
# The actual render (headless Chromium + Butterchurn WebGL + ffmpeg) runs on
# Ben's Latitude over Tailscale, not locally on the Pi -- a real browser
# compositor render is too heavy for Kip's ARM CPU. This script stages a
# local input file to Latitude if needed (a remote URL is fetched there
# directly via yt-dlp), SSHes in to run the unmodified render script, then
# copies the resulting MP4 back to the path the caller expects.

set -euo pipefail

KIP_HOME="${KIP_HOME:-{{HOME}}}"
export HOME="$KIP_HOME"

if [[ -f "$KIP_HOME/.openclaw/.env" ]]; then
  while IFS= read -r line; do
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
    [[ "$line" =~ ^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)= ]] || continue
    key="${BASH_REMATCH[1]}"
    [[ -n "${!key+x}" ]] && continue
    export "$line"
  done < "$KIP_HOME/.openclaw/.env"
fi

REMOTE_HOST="${MILKDROP_REMOTE_HOST:-kip-latitude}"
REMOTE_DIR="${MILKDROP_REMOTE_DIR:-/home/palewire/milkdrop}"
REMOTE_PATH="/home/palewire/.nvm/versions/node/v24.21.0/bin:/home/palewire/.local/bin:/usr/local/bin:/usr/bin:/bin"

# Split out --input / --output; pass everything else straight through
# unchanged (--duration, --start, --width, --height, --fps, --preset, --help,
# --keep-temp).
INPUT=""
OUTPUT=""
\1REDACTED
while [[ $# -gt 0 ]]; do
  case "$1" in
    --input)
      INPUT="$2"; shift 2 ;;
    --output)
      OUTPUT="$2"; shift 2 ;;
    --help|-h|--keep-temp)
      PASSTHROUGH+=("$1"); shift ;;
    *)
      PASSTHROUGH+=("$1" "$2"); shift 2 ;;
  esac
done

if [[ -z "$INPUT" ]]; then
  echo "--input is required" >&2
  exit 1
fi

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
if [[ -z "$OUTPUT" ]]; then
  OUTPUT="$KIP_HOME/.openclaw/media/outbound/milkdrop-${TIMESTAMP}.mp4"
fi
mkdir -p "$(dirname "$OUTPUT")"

REMOTE_INPUT="$INPUT"
REMOTE_OUTPUT="${REMOTE_DIR}/out/milkdrop-${TIMESTAMP}.mp4"
STAGED_REMOTE_INPUT=""

ssh "$REMOTE_HOST" "mkdir -p '${REMOTE_DIR}/in' '${REMOTE_DIR}/out'"

# Stage a local file to Latitude; a remote URL is fetched there directly by
# the render script's own yt-dlp step, so it just passes through unchanged.
if [[ ! "$INPUT" =~ ^https?:// ]]; then
  if [[ ! -f "$INPUT" ]]; then
    echo "Input file not found: $INPUT" >&2
    exit 1
  fi
  STAGED_REMOTE_INPUT="${REMOTE_DIR}/in/$(basename "$INPUT")"
  scp -q "$INPUT" "${REMOTE_HOST}:${STAGED_REMOTE_INPUT}"
  REMOTE_INPUT="$STAGED_REMOTE_INPUT"
fi

REMOTE_RESULT="$(ssh "$REMOTE_HOST" \
  "export PATH='${REMOTE_PATH}'; cd '${REMOTE_DIR}' && node render-milkdrop.mjs --input '${REMOTE_INPUT}' --output '${REMOTE_OUTPUT}' ${PASSTHROUGH[*]@Q}")"

[[ -n "$STAGED_REMOTE_INPUT" ]] && ssh "$REMOTE_HOST" "rm -f '${STAGED_REMOTE_INPUT}'" >/dev/null 2>&1 || true

SUMMARY_LINE="$(echo "$REMOTE_RESULT" | tail -1)"
if ! echo "$SUMMARY_LINE" | grep -q '"ok":true'; then
  echo "Remote render failed: $REMOTE_RESULT" >&2
  exit 1
fi

scp -q "${REMOTE_HOST}:${REMOTE_OUTPUT}" "$OUTPUT"
ssh "$REMOTE_HOST" "rm -f '${REMOTE_OUTPUT}'" >/dev/null 2>&1 || true

# Rewrite the JSON summary's path from the remote scratch path to the local
# delivery path the caller actually has on disk.
OUTPUT="$OUTPUT" SUMMARY_LINE="$SUMMARY_LINE" python3 -c "
import json, os
d = json.loads(os.environ['SUMMARY_LINE'])
d['path'] = os.environ['OUTPUT']
print(json.dumps(d))
"
