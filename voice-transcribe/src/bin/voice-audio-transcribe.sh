#!/bin/bash
# Usage: voice-transcription-runner.sh <input.ogg>
# Outputs transcript to stdout, exits non-zero on failure

set -eo pipefail

WHISPER_BIN="{{HOME}}/Code/whisper.cpp/build/bin/whisper-cli"
WHISPER_MODEL="{{HOME}}/Code/whisper.cpp/models/ggml-base.en-q5_0.bin"
export LD_LIBRARY_PATH="{{HOME}}/Code/whisper.cpp/build/src:{{HOME}}/Code/whisper.cpp/build/ggml/src${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT
INPUT="$1"

# Convert OGG/Opus to 16kHz mono WAV
ffmpeg -loglevel error -i "$INPUT" \
  -ar 16000 -ac 1 -c:a pcm_s16le \
  "$TMPDIR/audio.wav"

# Transcribe
TRANSCRIPT=$($WHISPER_BIN \
  -m "$WHISPER_MODEL" \
  -f "$TMPDIR/audio.wav" \
  -t 4 \
  --no-timestamps \
  --max-context 128 \
  -l en \
  --no-prints \
  2>/dev/null)

if [ -z "$TRANSCRIPT" ]; then
  echo "Error: transcription produced no output" >&2
  exit 1
fi

echo "$TRANSCRIPT"
