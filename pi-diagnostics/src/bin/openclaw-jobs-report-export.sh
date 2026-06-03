#!/bin/bash
# Snapshot OpenClaw cron job statuses to Google Sheet and kip-claw JSON.
source {{HOME}}/.openclaw/.env
if [ -n "${GOG_KEYRING_PASSWORD:-}" ]; then
  export GOG_KEYRING_PASSWORD
fi
export HOME="{{HOME}}"
export XDG_CONFIG_HOME="{{HOME}}/.config"
export PATH="/usr/local/bin:/usr/bin:/bin"
export GIT_TERMINAL_PROMPT=0
GOG_ACCOUNT="${GOG_ACCOUNT:-kip@palewi.re}"
DIAG_SHEET_ID="1xIMil5RtrnrHwRORIaV9wMJQPsvXDlDdyfVBiNmhBhI"
KIP_CLAW_JSON="{{HOME}}/kip-claw/src/lib/openclawJobs.json"
LOG="/tmp/kip-openclaw-jobs.log"
SCRIPT_START=$(date +%s)
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

trap 'DURATION=$(( $(date +%s) - SCRIPT_START )); bash {{HOME}}/bin/kip-cron-log.sh "kip-openclaw-jobs" "$?" "$DURATION" ""' EXIT

echo "[$TIMESTAMP] Collecting OpenClaw job statuses..." >> "$LOG"

# Fail early if Sheets access is unavailable in non-interactive mode.
if ! timeout 25s gog --no-input -a "$GOG_ACCOUNT" sheets get "$DIAG_SHEET_ID" "Cron Health!A1:A1" --json --results-only >/dev/null 2>&1 </dev/null; then
  echo "[$TIMESTAMP] Failed Sheets preflight for gog account '$GOG_ACCOUNT' (keyring locked/token unavailable). If using keyring_backend=file, set GOG_KEYRING_PASSWORD." >> "$LOG"
  exit 1
fi

timeout 180s python3 {{HOME}}/bin/openclaw-jobs-export-core.py \
  "$KIP_CLAW_JSON" \
  "$TIMESTAMP" \
  "{{HOME}}/.openclaw/cron/jobs.json" \
  "{{HOME}}/.openclaw/cron/jobs-state.json" \
  "$DIAG_SHEET_ID" \
  "$GOG_ACCOUNT" </dev/null >> "$LOG" 2>&1

if [ $? -ne 0 ]; then
  echo "[$TIMESTAMP] Failed to collect/export OpenClaw job statuses" >> "$LOG"
  exit 1
fi

git -C {{HOME}}/kip-claw add src/lib/openclawJobs.json
git -C {{HOME}}/kip-claw diff --cached --quiet || (
  git -C {{HOME}}/kip-claw commit -m "chore: update openclaw jobs data" &&
  timeout 120s git -C {{HOME}}/kip-claw pull --rebase --autostash origin main &&
  timeout 120s git -C {{HOME}}/kip-claw push origin main
)

echo "[$TIMESTAMP] OpenClaw jobs logged" >> "$LOG"
