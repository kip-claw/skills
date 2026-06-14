#!/usr/bin/env bash
# Convenience wrapper for the milkdrop OpenClaw skill.
# Sources ~/.openclaw/.env (e.g. MILKDROP_OUTPUT_DIR) without overriding values
# already present in the caller's environment, sets HOME, then dispatches to the
# Node renderer.

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

SKILL_DIR="$KIP_HOME/.openclaw/workspace/skills/milkdrop"

# Ensure yt-dlp / ffmpeg standalone installs are discoverable.
export PATH="/usr/local/bin:/usr/bin:$PATH"

NODE_BIN="$(command -v node || true)"
if [[ -z "$NODE_BIN" ]]; then
  echo "node is required but was not found on PATH." >&2
  exit 1
fi

exec "$NODE_BIN" "$SKILL_DIR/src/render-milkdrop.mjs" "$@"
