#!/usr/bin/env bash
# Convenience wrapper for the audiobook OpenClaw skill.
# Sources ~/.openclaw/.env so provider API keys + PIPER_* paths are available,
# then dispatches to the skill's Python entry point.

set -euo pipefail

KIP_HOME="${KIP_HOME:-{{HOME}}}"
export HOME="$KIP_HOME"

if [[ -f "$KIP_HOME/.openclaw/.env" ]]; then
  # Load env vars from ~/.openclaw/.env WITHOUT overriding values already
  # present in the caller's environment, so per-invocation overrides like
  # `PIPER_VOICE=... ~/bin/article-audiobook-render.sh ...` actually take effect.
  while IFS= read -r line; do
    # Skip blanks and comments
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
    # Match KEY=VALUE lines only
    [[ "$line" =~ ^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)= ]] || continue
    key="${BASH_REMATCH[1]}"
    # Skip keys already set in the environment
    [[ -n "${!key+x}" ]] && continue
    # Evaluate via `export` so quoted values / escapes behave as in `source`
    export "$line"
  done < "$KIP_HOME/.openclaw/.env"
fi

SKILL_DIR="$KIP_HOME/.openclaw/workspace/skills/audiobook"
PYTHON_BIN="$SKILL_DIR/.venv/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi
exec "$PYTHON_BIN" "$SKILL_DIR/audiobook.py" "$@"
