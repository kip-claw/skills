#!/bin/bash
# Snapshot runs log Google Sheet data to kip-claw JSON.
SCRIPT_START=$(date +%s)
trap 'DURATION=$(( $(date +%s) - SCRIPT_START )); bash {{HOME}}/bin/kip-cron-log.sh "kip-runs" "$?" "$DURATION" ""' EXIT

source {{HOME}}/.openclaw/.env
if [ -n "${GOG_KEYRING_PASSWORD:-}" ]; then
  export GOG_KEYRING_PASSWORD
fi
export HOME="{{HOME}}"
export XDG_CONFIG_HOME="{{HOME}}/.config"
export PATH="/usr/local/bin:/usr/bin:/bin"
export GIT_TERMINAL_PROMPT=0

GOG_ACCOUNT="${GOG_ACCOUNT:-kip@palewi.re}"
RUNS_SHEET_ID="1ybViNc3uJp9Be7Os5Cryu6E83VTxB0ZqWPRYYiQAMfA"
KIP_CLAW_JSON="{{HOME}}/kip-claw/static/data/runs.json"
LOG="/tmp/kip-runs.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$TIMESTAMP] Exporting runs data..." >> "$LOG"

# Preflight check for Sheets access
if ! timeout 25s gog --no-input -a "$GOG_ACCOUNT" sheets get "$RUNS_SHEET_ID" "Sheet1!A1:A1" --json --results-only >/dev/null 2>&1 </dev/null; then
  echo "[$TIMESTAMP] Failed Sheets preflight for gog account '$GOG_ACCOUNT'" >> "$LOG"
  exit 1
fi

timeout 180s python3 {{HOME}}/bin/runs-log-export-core.py \
  "$KIP_CLAW_JSON" \
  "$RUNS_SHEET_ID" \
  "$GOG_ACCOUNT" </dev/null >> "$LOG" 2>&1

if [ $? -ne 0 ]; then
  echo "[$TIMESTAMP] Failed to export runs data" >> "$LOG"
  exit 1
fi

git -C {{HOME}}/kip-claw add static/data/runs.json
git -C {{HOME}}/kip-claw diff --cached --quiet || (
  git -C {{HOME}}/kip-claw commit -m "chore: update runs data" &&
  timeout 120s git -C {{HOME}}/kip-claw pull --rebase --autostash origin main &&
  timeout 120s git -C {{HOME}}/kip-claw push origin main
)

echo "[$TIMESTAMP] Runs data exported" >> "$LOG"
