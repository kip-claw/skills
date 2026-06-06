#!/bin/bash
# Snapshot NYC list Google Sheet data to kip-claw JSON with geocoding.
set -euo pipefail

SCRIPT_START=$(date +%s)
trap 'DURATION=$(( $(date +%s) - SCRIPT_START )); bash {{HOME}}/bin/kip-cron-log.sh "kip-nyc-list" "$?" "$DURATION" "${CRON_NOTES:-}"' EXIT

source {{HOME}}/.openclaw/.env
if [ -n "${GOG_KEYRING_PASSWORD:-}" ]; then
  export GOG_KEYRING_PASSWORD
fi
if [ -n "${GOOGLE_MAPS_API_KEY:-}" ]; then
  export GOOGLE_MAPS_API_KEY
fi
export HOME="{{HOME}}"
export XDG_CONFIG_HOME="{{HOME}}/.config"
export PATH="/usr/local/bin:/usr/bin:/bin"
export GIT_TERMINAL_PROMPT=0

GOG_ACCOUNT="${GOG_ACCOUNT:-kip@palewi.re}"
NYC_SHEET_ID="1GeVkWdyqKM7P8A0MGwWns3fOketRR5ThnubSEaIKJEQ"
KIP_CLAW_JSON="{{HOME}}/Code/kip-claw/static/data/nycList.json"
GEOCACHE="{{HOME}}/Code/kip-claw/src/lib/nyc-geocache.json"
KIP_CLAW_REPO="{{HOME}}/Code/kip-claw"
PRETTIER="$KIP_CLAW_REPO/node_modules/.bin/prettier"
LOG="/tmp/kip-nyc-list.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$TIMESTAMP] Exporting NYC list data..." >> "$LOG"

# Preflight check for Sheets access
if ! timeout 25s gog --no-input -a "$GOG_ACCOUNT" sheets get "$NYC_SHEET_ID" "List!A1:A1" --json --results-only >/dev/null 2>&1 </dev/null; then
  echo "[$TIMESTAMP] Failed Sheets preflight for gog account '$GOG_ACCOUNT'" >> "$LOG"
  exit 1
fi

timeout 180s python3 {{HOME}}/bin/nyc-list-data-export-core.py \
  "$KIP_CLAW_JSON" \
  "$GEOCACHE" \
  "$NYC_SHEET_ID" \
  "$GOG_ACCOUNT" </dev/null >> "$LOG" 2>&1

if [ $? -ne 0 ]; then
  echo "[$TIMESTAMP] Failed to export NYC list data" >> "$LOG"
  exit 1
fi
# Ensure Prettier formatting compliance for generated JSON files
if [ ! -x "$PRETTIER" ]; then
  echo "[$TIMESTAMP] Failed: repo-local Prettier is unavailable at $PRETTIER" >> "$LOG"
  CRON_NOTES="failed: prettier unavailable"
  exit 1
fi
if ! (
  cd "$KIP_CLAW_REPO"
  "$PRETTIER" --write static/data/nycList.json src/lib/nyc-geocache.json
) >> "$LOG" 2>&1; then
  echo "[$TIMESTAMP] Failed: prettier formatting for NYC list data" >> "$LOG"
  CRON_NOTES="failed: prettier"
  exit 1
fi
git -C "$KIP_CLAW_REPO" add static/data/nycList.json src/lib/nyc-geocache.json

if git -C "$KIP_CLAW_REPO" diff --cached --quiet; then
  CRON_NOTES="no changes"
  echo "[$TIMESTAMP] No nyc list changes to commit" >> "$LOG"
else
  if ! git -C "$KIP_CLAW_REPO" commit --no-verify -m "chore: update nyc list data" >> "$LOG" 2>&1; then
    echo "[$TIMESTAMP] Failed: git commit for nyc list data" >> "$LOG"
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

echo "[$TIMESTAMP] NYC list data exported" >> "$LOG"
