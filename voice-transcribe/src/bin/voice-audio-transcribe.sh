#!/bin/bash
# Usage: voice-transcription-runner.sh <input.ogg>
# Outputs transcript to stdout, exits non-zero on failure.
#
# Telegram voice notes are transcribed by the authenticated whisper.cpp service
# on Ben's Latitude over Tailscale. The Pi logs only service diagnostics: no
# audio, filenames, or transcript text are retained in diagnostics.

set -uo pipefail

REMOTE_URL="${WHISPER_REMOTE_URL:-http://100.125.75.72:8178/inference}"
\1REDACTED
LOG_SCRIPT="{{HOME}}/bin/whisper-transcription-log.sh"
MODEL="Whisper base.en Q5_0"
TMPDIR=$(mktemp -d)
START_MS=$(date +%s%3N)
AUDIO_SECONDS=0
PROCESSING_MS=0
OUTCOME=error
STATUS=unknown
trap 'rc=$?; end_ms=$(date +%s%3N); total_ms=$((end_ms - START_MS)); rtf=$(awk -v p="$PROCESSING_MS" -v a="$AUDIO_SECONDS" "BEGIN { if (a > 0) printf \"%.4f\", p / (a * 1000); else print 0 }"); "$LOG_SCRIPT" "$OUTCOME" "$AUDIO_SECONDS" "$total_ms" "$PROCESSING_MS" "$rtf" "$MODEL" "$STATUS" >/dev/null 2>&1 & rm -rf "$TMPDIR"; exit "$rc"' EXIT

INPUT="$1"
WAV="$TMPDIR/audio.wav"
RESPONSE="$TMPDIR/remote.json"

if [ ! -r "$TOKEN_FILE" ]; then
  STATUS=missing_token
  echo "Error: remote transcription token is unavailable" >&2
  exit 1
fi

if ! ffmpeg -loglevel error -i "$INPUT" -ar 16000 -ac 1 -c:a pcm_s16le "$WAV"; then
  STATUS=audio_conversion_failed
  exit 1
fi
AUDIO_SECONDS=$(ffprobe -v error -show_entries format=duration -of default=nk=1:nw=1 "$WAV" 2>/dev/null || echo 0)

HTTP_STATUS=$(curl --silent --show-error --output "$RESPONSE" --write-out '%{http_code}' --max-time 180 \
  -H "Authorization: Bearer $(cat "$TOKEN_FILE")" \
  -F "file=@${WAV};type=audio/wav" \
  "$REMOTE_URL")
CURL_RC=$?
if [ "$CURL_RC" -ne 0 ]; then
  STATUS=curl_error
  echo "Error: remote transcription request failed" >&2
  exit 1
fi
if [ "$HTTP_STATUS" != 200 ]; then
  STATUS="http_${HTTP_STATUS}"
  echo "Error: remote transcription service returned HTTP ${HTTP_STATUS}" >&2
  exit 1
fi

TRANSCRIPT=$(jq -er '.text | strings | select(length > 0)' "$RESPONSE")
if [ $? -ne 0 ]; then
  STATUS=invalid_response
  echo "Error: remote transcription service returned no transcript" >&2
  exit 1
fi
PROCESSING_MS=$(jq -er '.elapsedMs | numbers' "$RESPONSE" 2>/dev/null || echo 0)
MODEL=$(jq -er '.model | strings | select(length > 0)' "$RESPONSE" 2>/dev/null || echo "$MODEL")
OUTCOME=success
STATUS=http_200
printf '%s\n' "$TRANSCRIPT"
