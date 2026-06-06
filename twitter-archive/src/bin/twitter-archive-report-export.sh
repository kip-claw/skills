#!/bin/bash
# Export Twitter archive summary from NAS birdclaw backup to kip-claw JSON.
set -euo pipefail

SCRIPT_START=$(date +%s)
trap 'DURATION=$(( $(date +%s) - SCRIPT_START )); bash {{HOME}}/bin/kip-cron-log.sh "kip-twitter-export" "$?" "$DURATION" "${CRON_NOTES:-}"' EXIT

export HOME="{{HOME}}"
export PATH="/usr/local/bin:/usr/bin:/bin"
export GIT_TERMINAL_PROMPT=0
NAS_SSH_TARGET="nas@100.118.154.80"

KIP_CLAW_REPO="{{HOME}}/Code/kip-claw"
KIP_CLAW_JSON="$KIP_CLAW_REPO/static/data/twitterArchive.json"
PRETTIER="$KIP_CLAW_REPO/node_modules/.bin/prettier"
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

if [ ! -x "$PRETTIER" ]; then
  echo "[$TIMESTAMP] Failed: repo-local Prettier is unavailable at $PRETTIER" >> "$LOG"
  CRON_NOTES="failed: prettier unavailable"
  exit 1
fi

if ! (
  cd "$KIP_CLAW_REPO"
  "$PRETTIER" --write static/data/twitterArchive.json
) >> "$LOG" 2>&1; then
  echo "[$TIMESTAMP] Failed: prettier formatting for twitterArchive.json" >> "$LOG"
  CRON_NOTES="failed: prettier"
  exit 1
fi

git -C "$KIP_CLAW_REPO" add static/data/twitterArchive.json
if git -C "$KIP_CLAW_REPO" diff --cached --quiet; then
  CRON_NOTES="no changes"
  echo "[$TIMESTAMP] No twitter archive changes to commit" >> "$LOG"
else
  if ! git -C "$KIP_CLAW_REPO" commit --no-verify -m "chore: update twitter archive data" >> "$LOG" 2>&1; then
    echo "[$TIMESTAMP] Failed: git commit for twitter archive data" >> "$LOG"
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

echo "[$TIMESTAMP] Twitter archive data exported" >> "$LOG"
