#!/bin/bash
# Check Cloudflare-managed domains, optionally log to Google Sheets, and export kip-claw JSON.
SCRIPT_START=$(date +%s)
trap 'DURATION=$(( $(date +%s) - SCRIPT_START )); bash {{HOME}}/bin/kip-cron-log.sh "kip-cloudflare-domains" "$?" "$DURATION" "${CRON_NOTES:-}"' EXIT

set -a
source {{HOME}}/.openclaw/.env
set +a

export HOME="{{HOME}}"
export XDG_CONFIG_HOME="{{HOME}}/.config"
export GIT_TERMINAL_PROMPT=0
export PATH="/usr/local/bin:/usr/bin:/bin"

LOCKFILE="/tmp/kip-cloudflare-domains.lock"
exec 9>"$LOCKFILE"
if ! flock -n 9; then
  DATE=$(date '+%Y-%m-%d %H:%M:%S')
  echo "[$DATE] Skipped: another cloudflare-domain-check run is already in progress" >> "{{HOME}}/.openclaw/logs/kip-cloudflare-domains.log"
  CRON_NOTES="skipped: already running"
  exit 0
fi

GOG_ACCOUNT="${GOG_ACCOUNT:-kip@palewi.re}"
SHEET_ID="${CLOUDFLARE_DOMAINS_SHEET_ID:-}"
SHEET_RANGE="Checks!A:P"
KIP_CLAW_REPO="{{HOME}}/Code/kip-claw"
KIP_CLAW_JSON="$KIP_CLAW_REPO/static/data/cloudflareDomains.json"
PRETTIER="$KIP_CLAW_REPO/node_modules/.bin/prettier"
VALUES_JSON="/tmp/kip-cloudflare-domains-values.json"
SUMMARY_JSON="/tmp/kip-cloudflare-domains-summary.json"
LOG="{{HOME}}/.openclaw/logs/kip-cloudflare-domains.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$DATE] Checking Cloudflare domains..." >> "$LOG"

if ! python3 {{HOME}}/bin/cloudflare-domain-monitor-core.py \
  --json-path "$KIP_CLAW_JSON" \
  --values-json-path "$VALUES_JSON" \
  --summary-path "$SUMMARY_JSON" >> "$LOG" 2>&1; then
  echo "[$DATE] Failed to collect Cloudflare domain checks" >> "$LOG"
  CRON_NOTES="collection failed"
  exit 1
fi

SUMMARY=$(cat "$SUMMARY_JSON" 2>/dev/null || echo '{}')
CRON_NOTES=$(python3 - "$SUMMARY" <<'PY'
import json
import sys
summary = json.loads(sys.argv[1])
print(f"checked={summary.get('total', 0)} ok={summary.get('ok', 0)} warn={summary.get('warn', 0)} fail={summary.get('fail', 0)}")
PY
)

if [ -n "$SHEET_ID" ]; then
  if ! timeout 30s gog --no-input -a "$GOG_ACCOUNT" sheets get "$SHEET_ID" "Checks!A1:A1" --json --results-only >/dev/null 2>&1 </dev/null; then
    echo "[$DATE] Failed: could not read Cloudflare domain monitor sheet" >> "$LOG"
    exit 1
  fi

  VALUES=$(cat "$VALUES_JSON")
  if ! timeout 60s gog --no-input -a "$GOG_ACCOUNT" sheets append "$SHEET_ID" "$SHEET_RANGE" \
    --values-json "$VALUES" \
    --insert INSERT_ROWS >> "$LOG" 2>&1 </dev/null; then
    echo "[$DATE] Failed: could not append Cloudflare domain checks to sheet" >> "$LOG"
    exit 1
  fi
else
  echo "[$DATE] CLOUDFLARE_DOMAINS_SHEET_ID is not set; skipped Google Sheet append" >> "$LOG"
fi

if [ ! -x "$PRETTIER" ]; then
  echo "[$DATE] Failed: repo-local Prettier is unavailable at $PRETTIER" >> "$LOG"
  CRON_NOTES="failed: prettier unavailable"
  exit 1
fi

if ! (
  cd "$KIP_CLAW_REPO"
  "$PRETTIER" --write static/data/cloudflareDomains.json
) >> "$LOG" 2>&1; then
  echo "[$DATE] Failed: prettier formatting for cloudflareDomains.json" >> "$LOG"
  CRON_NOTES="failed: prettier"
  exit 1
fi

git -C "$KIP_CLAW_REPO" add static/data/cloudflareDomains.json

if ! git -C "$KIP_CLAW_REPO" diff --cached --quiet; then
  if ! git -C "$KIP_CLAW_REPO" commit --no-verify -m "chore: update cloudflare domain data" >> "$LOG" 2>&1; then
    echo "[$DATE] Failed: git commit for cloudflareDomains.json" >> "$LOG"
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

  echo "[$DATE] Published cloudflareDomains.json to kip-claw/main" >> "$LOG"
else
  echo "[$DATE] No cloudflareDomains.json changes to commit" >> "$LOG"
fi

echo "[$DATE] Done: $CRON_NOTES" >> "$LOG"
