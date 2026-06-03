#!/bin/bash
# Export Twitter archive summary from NAS birdclaw backup to kip-claw JSON.
SCRIPT_START=$(date +%s)
trap 'DURATION=$(( $(date +%s) - SCRIPT_START )); bash {{HOME}}/bin/kip-cron-log.sh "kip-twitter-export" "$?" "$DURATION" ""' EXIT

export HOME="{{HOME}}"
export PATH="/usr/local/bin:/usr/bin:/bin"
export GIT_TERMINAL_PROMPT=0
NAS_SSH_TARGET="nas@100.118.154.80"

KIP_CLAW_JSON="{{HOME}}/kip-claw/static/data/twitterArchive.json"
LOG="/tmp/kip-twitter-export.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$TIMESTAMP] Exporting Twitter archive data..." >> "$LOG"

# Preflight: verify NAS is reachable
if ! timeout 10s ssh -i {{HOME}}/.ssh/nas_key -o ConnectTimeout=5 -o StrictHostKeyChecking=no "$NAS_SSH_TARGET" "true" </dev/null >/dev/null 2>&1; then
  echo "[$TIMESTAMP] NAS unreachable" >> "$LOG"
  exit 1
fi

timeout 300s python3 {{HOME}}/bin/twitter-archive-export-core.py \
  "$KIP_CLAW_JSON" </dev/null >> "$LOG" 2>&1

if [ $? -ne 0 ]; then
  echo "[$TIMESTAMP] Failed to export Twitter archive data" >> "$LOG"
  exit 1
fi

git -C {{HOME}}/kip-claw add static/data/twitterArchive.json
git -C {{HOME}}/kip-claw diff --cached --quiet || (
  git -C {{HOME}}/kip-claw commit -m "chore: update twitter archive data" &&
  timeout 120s git -C {{HOME}}/kip-claw pull --rebase --autostash origin main &&
  timeout 120s git -C {{HOME}}/kip-claw push origin main
)

echo "[$TIMESTAMP] Twitter archive data exported" >> "$LOG"
