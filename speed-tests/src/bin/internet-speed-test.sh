#!/bin/bash
SCRIPT_START=$(date +%s)
trap 'DURATION=$(( $(date +%s) - SCRIPT_START )); bash {{HOME}}/bin/kip-cron-log.sh "kip-speedtest" "$?" "$DURATION" ""' EXIT
source {{HOME}}/.openclaw/.env

# Ensure gog uses kip's persisted config/keyring in service/non-login contexts.
export HOME="{{HOME}}"
export XDG_CONFIG_HOME="{{HOME}}/.config"
export GIT_TERMINAL_PROMPT=0

SHEET_ID="1_YH3KLAGSNzATkSUf9UEtFYhgA5s_R7IV-CFC_fye-s"
export GOG_KEYRING_PASSWORD="${GOG_KEYRING_PASSWORD}"
GOG_ACCOUNT="${GOG_ACCOUNT:-kip@palewi.re}"
SHEET_RANGE="Sheet1!A:F"
KIP_CLAW_REPO="{{HOME}}/Code/kip-claw"
KIP_CLAW_JSON="$KIP_CLAW_REPO/static/data/speedTests.json"
PRETTIER="$KIP_CLAW_REPO/node_modules/.bin/prettier"
LOG="/var/log/kip-speedtest.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$DATE] Running speed test..." >> "$LOG"

RESULT=$(speedtest-cli --json --secure 2>/dev/null)

if [ -z "$RESULT" ]; then
  echo "[$DATE] Speed test failed — no output" >> "$LOG"
  exit 1
fi

PARSED=$(echo "$RESULT" | python3 {{HOME}}/bin/network-speedtest-parse-core.py)
IFS='|' read -r DOWNLOAD UPLOAD PING SERVER SPONSOR <<< "$PARSED"

if [ -z "${DOWNLOAD:-}" ] || [ -z "${UPLOAD:-}" ] || [ -z "${PING:-}" ]; then
  echo "[$DATE] Failed: could not parse speed test output" >> "$LOG"
  exit 1
fi

AUTH_LIST=$(gog --no-input auth list --plain 2>>"$LOG")
if [ $? -ne 0 ]; then
  echo "[$DATE] Failed to read gog token store (non-interactive auth failed)" >> "$LOG"
  exit 1
fi

echo "$AUTH_LIST" | awk '{print $1}' | grep -Fxq "$GOG_ACCOUNT"
if [ $? -ne 0 ]; then
  echo "[$DATE] gog account not found in token store: $GOG_ACCOUNT" >> "$LOG"
  exit 1
fi

gog --no-input -a "$GOG_ACCOUNT" sheets append "$SHEET_ID" "$SHEET_RANGE" \
  "$DATE|$PARSED"

if [ $? -eq 0 ]; then
  python3 {{HOME}}/bin/network-speedtest-export-core.py \
    "$KIP_CLAW_JSON" "$DATE" "$DOWNLOAD" "$UPLOAD" "$PING" "$SERVER" "$SPONSOR"

  if [ $? -ne 0 ]; then
    echo "[$DATE] Failed: could not export JSON for kip-claw" >> "$LOG"
    exit 1
  fi

  if [ ! -x "$PRETTIER" ]; then
    echo "[$DATE] Failed: repo-local Prettier is unavailable at $PRETTIER" >> "$LOG"
    exit 1
  fi

  if ! (
    cd "$KIP_CLAW_REPO"
    "$PRETTIER" --write static/data/speedTests.json
  ) >> "$LOG" 2>&1; then
    echo "[$DATE] Failed: prettier formatting for speedTests.json" >> "$LOG"
    exit 1
  fi

  git -C "$KIP_CLAW_REPO" add static/data/speedTests.json

  if ! git -C "$KIP_CLAW_REPO" diff --cached --quiet; then
    if ! git -C "$KIP_CLAW_REPO" commit --no-verify -m "chore: update speed test data" >> "$LOG" 2>&1; then
      echo "[$DATE] Failed: git commit for speedTests.json" >> "$LOG"
      exit 1
    fi

    if ! timeout 120s git -C "$KIP_CLAW_REPO" pull --rebase --autostash origin main >> "$LOG" 2>&1; then
      echo "[$DATE] Failed: git pull --rebase for kip-claw" >> "$LOG"
      exit 1
    fi

    if ! timeout 120s git -C "$KIP_CLAW_REPO" push origin main >> "$LOG" 2>&1; then
      echo "[$DATE] Failed: git push origin main for kip-claw" >> "$LOG"
      exit 1
    fi

    echo "[$DATE] Published speedTests.json to kip-claw/main" >> "$LOG"
  else
    echo "[$DATE] No speedTests.json changes to commit" >> "$LOG"
  fi

  echo "[$DATE] Logged — Down: ${DOWNLOAD} Mbps, Up: ${UPLOAD} Mbps, Ping: ${PING}ms" >> "$LOG"
else
  echo "[$DATE] Failed to write to sheet" >> "$LOG"
  exit 1
fi
