#!/bin/bash
# Snapshot NYC list Google Sheet data to kip-claw JSON with geocoding.
SCRIPT_START=$(date +%s)
trap 'DURATION=$(( $(date +%s) - SCRIPT_START )); bash {{HOME}}/bin/kip-cron-log.sh "kip-nyc-list" "$?" "$DURATION" ""' EXIT

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
KIP_CLAW_JSON="{{HOME}}/kip-claw/static/data/nycList.json"
GEOCACHE="{{HOME}}/kip-claw/src/lib/nyc-geocache.json"
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

git -C {{HOME}}/kip-claw add static/data/nycList.json src/lib/nyc-geocache.json
git -C {{HOME}}/kip-claw diff --cached --quiet || (
  git -C {{HOME}}/kip-claw commit -m "chore: update nyc list data" &&
  timeout 120s git -C {{HOME}}/kip-claw pull --rebase --autostash origin main &&
  timeout 120s git -C {{HOME}}/kip-claw push origin main
)

echo "[$TIMESTAMP] NYC list data exported" >> "$LOG"
