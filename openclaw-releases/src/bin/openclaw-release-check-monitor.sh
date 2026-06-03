#!/bin/bash
# Check for new OpenClaw releases and print version info.
# Exits 0 with JSON output if a new version is available, exits 2 if already up to date.
set -euo pipefail

export HOME="{{HOME}}"
export PATH="/usr/local/bin:/usr/bin:/bin"

CURRENT=$(openclaw --version 2>/dev/null | awk '{print $2}')
LATEST=$(npm view openclaw version 2>/dev/null)

if [ -z "$CURRENT" ] || [ -z "$LATEST" ]; then
  echo "ERROR: Could not determine openclaw versions" >&2
  exit 1
fi

if [ "$CURRENT" = "$LATEST" ]; then
  echo "{\"current\": \"$CURRENT\", \"latest\": \"$LATEST\", \"update_available\": false}"
  exit 2
fi

echo "{\"current\": \"$CURRENT\", \"latest\": \"$LATEST\", \"update_available\": true}"
exit 0
