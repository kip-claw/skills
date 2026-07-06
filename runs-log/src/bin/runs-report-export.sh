#!/bin/bash
# Snapshot runs log Google Sheet data to kip-claw JSON.
set -euo pipefail

SCRIPT_START=$(date +%s)

on_exit() {
  local rc="$?"
  local duration=$(( $(date +%s) - SCRIPT_START ))
  bash {{HOME}}/bin/kip-cron-log.sh "kip-runs" "$rc" "$duration" "${CRON_NOTES:-}" || true
  exit "$rc"
}
trap on_exit EXIT

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
KIP_CLAW_REPO="{{HOME}}/Code/kip-claw"
KIP_CLAW_JSON="$KIP_CLAW_REPO/static/data/runs.json"
PRETTIER="$KIP_CLAW_REPO/node_modules/.bin/prettier"
LOG="/tmp/kip-runs.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

format_repo_for_push() {
  local check_out=""
  local -a bad_files=()

  if check_out=$(cd "$KIP_CLAW_REPO" && "$PRETTIER" --check . 2>&1); then
    return 0
  fi

  mapfile -t bad_files < <(printf '%s\n' "$check_out" | sed -n 's/^\[warn\] \(.*\)$/\1/p')
  if [ ${#bad_files[@]} -eq 0 ]; then
    echo "[$TIMESTAMP] Failed: prettier --check reported errors but no file list" >> "$LOG"
    CRON_NOTES="failed: prettier-check"
    return 1
  fi

  echo "[$TIMESTAMP] Formatting ${#bad_files[@]} file(s) to satisfy pre-push lint" >> "$LOG"
  if ! (
    cd "$KIP_CLAW_REPO"
    "$PRETTIER" --write "${bad_files[@]}"
  ) >> "$LOG" 2>&1; then
    echo "[$TIMESTAMP] Failed: prettier --write on lint-failing files" >> "$LOG"
    CRON_NOTES="failed: prettier-fix"
    return 1
  fi

  git -C "$KIP_CLAW_REPO" add -- "${bad_files[@]}"

  if ! (
    cd "$KIP_CLAW_REPO"
    "$PRETTIER" --check .
  ) >> "$LOG" 2>&1; then
    echo "[$TIMESTAMP] Failed: prettier --check still failing after auto-format" >> "$LOG"
    CRON_NOTES="failed: prettier-check"
    return 1
  fi

  return 0
}

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

if [ ! -x "$PRETTIER" ]; then
  echo "[$TIMESTAMP] Failed: repo-local Prettier is unavailable at $PRETTIER" >> "$LOG"
  CRON_NOTES="failed: prettier unavailable"
  exit 1
fi

if ! (
  cd "$KIP_CLAW_REPO"
  "$PRETTIER" --write static/data/runs.json
) >> "$LOG" 2>&1; then
  echo "[$TIMESTAMP] Failed: prettier formatting for runs.json" >> "$LOG"
  CRON_NOTES="failed: prettier"
  exit 1
fi

git -C "$KIP_CLAW_REPO" add static/data/runs.json
if ! format_repo_for_push; then
  exit 1
fi

if git -C "$KIP_CLAW_REPO" diff --cached --quiet; then
  CRON_NOTES="no changes"
  echo "[$TIMESTAMP] No runs changes to commit" >> "$LOG"
else
  if ! git -C "$KIP_CLAW_REPO" commit --no-verify -m "chore: update runs data" >> "$LOG" 2>&1; then
    echo "[$TIMESTAMP] Failed: git commit for runs data" >> "$LOG"
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

echo "[$TIMESTAMP] Runs data exported" >> "$LOG"
