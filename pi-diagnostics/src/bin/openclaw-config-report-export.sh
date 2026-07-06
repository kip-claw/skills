#!/bin/bash
# Snapshot OpenClaw config metadata to Google Sheet and kip-claw JSON.
set -euo pipefail

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
KIP_CLAW_JSON="{{HOME}}/Code/kip-claw/src/lib/openclawConfig.json"
KIP_CLAW_REPO="{{HOME}}/Code/kip-claw"
PRETTIER="$KIP_CLAW_REPO/node_modules/.bin/prettier"
LOG="/tmp/kip-openclaw-config.log"
SCRIPT_START=$(date +%s)
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

on_exit() {
  local rc="$?"
  local duration=$(( $(date +%s) - SCRIPT_START ))
  bash {{HOME}}/bin/kip-cron-log.sh "kip-openclaw-config" "$rc" "$duration" "${CRON_NOTES:-}" || true
  exit "$rc"
}
trap on_exit EXIT

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

echo "[$TIMESTAMP] Collecting OpenClaw config snapshot..." >> "$LOG"

# Fail early if Sheets access is unavailable in non-interactive mode.
if ! timeout 25s gog --no-input -a "$GOG_ACCOUNT" sheets get "$DIAG_SHEET_ID" "Cron Health!A1:A1" --json --results-only >/dev/null 2>&1 </dev/null; then
  echo "[$TIMESTAMP] Failed Sheets preflight for gog account '$GOG_ACCOUNT' (keyring locked/token unavailable). If using keyring_backend=file, set GOG_KEYRING_PASSWORD." >> "$LOG"
  exit 1
fi

timeout 180s python3 {{HOME}}/bin/openclaw-config-export-core.py \
  "$KIP_CLAW_JSON" \
  "$TIMESTAMP" \
  "{{HOME}}/.openclaw/openclaw.json" \
  "{{HOME}}/.openclaw/update-check.json" \
  "$DIAG_SHEET_ID" \
  "$GOG_ACCOUNT" </dev/null >> "$LOG" 2>&1

if [ $? -ne 0 ]; then
  echo "[$TIMESTAMP] Failed to collect/export OpenClaw config" >> "$LOG"
  exit 1
fi

if [ ! -x "$PRETTIER" ]; then
  echo "[$TIMESTAMP] Failed: repo-local Prettier is unavailable at $PRETTIER" >> "$LOG"
  CRON_NOTES="failed: prettier unavailable"
  exit 1
fi
if ! (
  cd "$KIP_CLAW_REPO"
  "$PRETTIER" --write src/lib/openclawConfig.json
) >> "$LOG" 2>&1; then
  echo "[$TIMESTAMP] Failed: prettier formatting for OpenClaw config data" >> "$LOG"
  CRON_NOTES="failed: prettier"
  exit 1
fi

git -C "$KIP_CLAW_REPO" add src/lib/openclawConfig.json
if ! format_repo_for_push; then
  exit 1
fi

if git -C "$KIP_CLAW_REPO" diff --cached --quiet; then
  CRON_NOTES="no changes"
  echo "[$TIMESTAMP] No openclaw config changes to commit" >> "$LOG"
else
  if ! git -C "$KIP_CLAW_REPO" commit --no-verify -m "chore: update openclaw config data" >> "$LOG" 2>&1; then
    echo "[$TIMESTAMP] Failed: git commit for openclaw config data" >> "$LOG"
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

echo "[$TIMESTAMP] OpenClaw config logged" >> "$LOG"
