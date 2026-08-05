#!/bin/bash
# Snapshot OpenClaw memory index metrics to kip-claw JSON.
set -euo pipefail

source {{HOME}}/.openclaw/.env
if [ -n "${GOG_KEYRING_PASSWORD:-}" ]; then
  export GOG_KEYRING_PASSWORD
fi
export HOME="{{HOME}}"
export XDG_CONFIG_HOME="{{HOME}}/.config"
export PATH="/usr/local/bin:/usr/bin:/bin"
export GIT_TERMINAL_PROMPT=0

KIP_CLAW_JSON="{{HOME}}/Code/kip-claw/src/lib/openclawMemory.json"
KIP_CLAW_MAP_JSON="{{HOME}}/Code/kip-claw/src/lib/openclawMemoryMap.json"
KIP_CLAW_REPO="{{HOME}}/Code/kip-claw"
PRETTIER="$KIP_CLAW_REPO/node_modules/.bin/prettier"
LOG="/tmp/kip-openclaw-memory.log"
SCRIPT_START=$(date +%s)
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
STATUS_JSON=$(mktemp)
MEMORY_DB="{{HOME}}/.openclaw/agents/main/agent/openclaw-agent.sqlite"

cleanup() {
  local status=$?
  local duration=$(( $(date +%s) - SCRIPT_START ))
  rm -f "$STATUS_JSON"
  bash {{HOME}}/bin/kip-cron-log.sh "kip-openclaw-memory" "$status" "$duration" "${CRON_NOTES:-}"
  exit "$status"
}
trap cleanup EXIT

echo "[$TIMESTAMP] Collecting OpenClaw memory status snapshot..." >> "$LOG"

if ! timeout 120s openclaw memory status --deep --json > "$STATUS_JSON"; then
  echo "[$TIMESTAMP] Failed to retrieve OpenClaw memory status" >> "$LOG"
  CRON_NOTES="failed: memory status"
  exit 1
fi

if ! timeout 180s python3 {{HOME}}/bin/openclaw-memory-map-export-core.py \
  "$KIP_CLAW_MAP_JSON" \
  "$TIMESTAMP" \
  "$MEMORY_DB" </dev/null >> "$LOG" 2>&1; then
  echo "[$TIMESTAMP] Failed to export OpenClaw memory semantic map" >> "$LOG"
  CRON_NOTES="failed: map export"
  exit 1
fi

if ! timeout 120s python3 {{HOME}}/bin/openclaw-memory-export-core.py \
  "$KIP_CLAW_JSON" \
  "$TIMESTAMP" \
  "$STATUS_JSON" </dev/null >> "$LOG" 2>&1; then
  echo "[$TIMESTAMP] Failed to export OpenClaw memory snapshot" >> "$LOG"
  CRON_NOTES="failed: export"
  exit 1
fi

if [ ! -x "$PRETTIER" ]; then
  echo "[$TIMESTAMP] Failed: repo-local Prettier is unavailable at $PRETTIER" >> "$LOG"
  CRON_NOTES="failed: prettier unavailable"
  exit 1
fi

if ! (
  cd "$KIP_CLAW_REPO"
  "$PRETTIER" --write src/lib/openclawMemory.json src/lib/openclawMemoryMap.json
) >> "$LOG" 2>&1; then
  echo "[$TIMESTAMP] Failed: prettier formatting for OpenClaw memory data" >> "$LOG"
  CRON_NOTES="failed: prettier"
  exit 1
fi

git -C "$KIP_CLAW_REPO" add src/lib/openclawMemory.json src/lib/openclawMemoryMap.json
if git -C "$KIP_CLAW_REPO" diff --cached --quiet; then
  CRON_NOTES="no changes"
  echo "[$TIMESTAMP] No openclaw memory changes to commit" >> "$LOG"
else
  if ! git -C "$KIP_CLAW_REPO" commit --no-verify -m "chore: update openclaw memory data" >> "$LOG" 2>&1; then
    echo "[$TIMESTAMP] Failed: git commit for openclaw memory data" >> "$LOG"
    CRON_NOTES="failed: commit"
    exit 1
  fi
  if ! timeout 120s git -C "$KIP_CLAW_REPO" pull --rebase --autostash origin main >> "$LOG" 2>&1; then
    echo "[$TIMESTAMP] Failed: git pull --rebase for kip-claw" >> "$LOG"
    CRON_NOTES="failed: pull"
    exit 1
  fi
  if ! timeout 120s git -C "$KIP_CLAW_REPO" push origin main >> "$LOG" 2>&1; then
    echo "[$TIMESTAMP] Failed: git push for kip-claw" >> "$LOG"
    CRON_NOTES="failed: push"
    exit 1
  fi
  CRON_NOTES="updated"
fi

echo "[$TIMESTAMP] OpenClaw memory status logged" >> "$LOG"
