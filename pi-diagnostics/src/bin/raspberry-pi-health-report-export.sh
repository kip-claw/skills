#!/bin/bash
# Collect Pi hardware health metrics, log to Google Sheet, and export to kip-claw JSON.
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
KIP_CLAW_JSON="{{HOME}}/Code/kip-claw/src/lib/piHealth.json"
LOG="/tmp/kip-pi-health.log"
SCRIPT_START=$(date +%s)
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

trap 'DURATION=$(( $(date +%s) - SCRIPT_START )); bash {{HOME}}/bin/kip-cron-log.sh "kip-pi-health" "$?" "$DURATION" "${CRON_NOTES:-}"' EXIT

echo "[$TIMESTAMP] Collecting Pi health metrics..." >> "$LOG"

# CPU temperature (millidegrees → degrees)
CPU_TEMP_RAW=$(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null || echo "0")
CPU_TEMP=$(echo "scale=1; $CPU_TEMP_RAW / 1000" | bc)

# GPU temperature via vcgencmd
GPU_TEMP=$(vcgencmd measure_temp 2>/dev/null | grep -oP '[0-9.]+' || echo "")

# CPU load averages
read LOAD1 LOAD5 LOAD15 REST < /proc/loadavg

# RAM (in MB)
RAM_TOTAL=$(awk '/^MemTotal:/{print int($2/1024)}' /proc/meminfo)
RAM_AVAILABLE=$(awk '/^MemAvailable:/{print int($2/1024)}' /proc/meminfo)
RAM_USED=$(( RAM_TOTAL - RAM_AVAILABLE ))

# Disk usage for / (in GB, strip 'G' suffix)
DISK_INFO=$(df -BG / | awk 'NR==2{gsub("G",""); print $2, $3}')
DISK_TOTAL=$(echo $DISK_INFO | awk '{print $1}')
DISK_USED=$(echo $DISK_INFO | awk '{print $2}')

# Uptime in days (2 decimal places)
UPTIME_SECS=$(awk '{print int($1)}' /proc/uptime)
UPTIME_DAYS=$(echo "scale=2; $UPTIME_SECS / 86400" | bc)

# Fail early if Sheets access is unavailable in non-interactive mode.
if ! timeout 25s gog --no-input -a "$GOG_ACCOUNT" sheets get "$DIAG_SHEET_ID" "Cron Health!A1:A1" --json --results-only >/dev/null 2>&1 </dev/null; then
  echo "[$TIMESTAMP] Failed Sheets preflight for gog account '$GOG_ACCOUNT' (keyring locked/token unavailable). If using keyring_backend=file, set GOG_KEYRING_PASSWORD." >> "$LOG"
  exit 1
fi

# Write to Google Sheet
timeout 90s gog --no-input -a "$GOG_ACCOUNT" sheets append "$DIAG_SHEET_ID" "Pi Health!A:K" \
  --values-json "[[\"$TIMESTAMP\",\"$CPU_TEMP\",\"$GPU_TEMP\",\"$LOAD1\",\"$LOAD5\",\"$LOAD15\",\"$RAM_USED\",\"$RAM_TOTAL\",\"$DISK_USED\",\"$DISK_TOTAL\",\"$UPTIME_DAYS\"]]" \
  --insert INSERT_ROWS </dev/null >> "$LOG" 2>&1

if [ $? -ne 0 ]; then
  echo "[$TIMESTAMP] Failed to write Pi health row to Google Sheet" >> "$LOG"
  exit 1
fi

# Export to kip-claw JSON
python3 {{HOME}}/bin/pi-health-export-core.py \
  "$KIP_CLAW_JSON" "$TIMESTAMP" "$CPU_TEMP" "$GPU_TEMP" \
  "$LOAD1" "$LOAD5" "$LOAD15" \
  "$RAM_USED" "$RAM_TOTAL" "$DISK_USED" "$DISK_TOTAL" "$UPTIME_DAYS"

if [ $? -ne 0 ]; then
  echo "[$TIMESTAMP] Warning: failed to export JSON for kip-claw" >> "$LOG"
fi
# Ensure Prettier formatting compliance
if command -v npx &>/dev/null; then
  if ! npx --yes prettier --write "$KIP_CLAW_JSON" >> "$LOG" 2>&1; then
    echo "[$TIMESTAMP] Warning: prettier formatting failed for pi health JSON" >> "$LOG"
  fi
fi
git -C {{HOME}}/Code/kip-claw add src/lib/piHealth.json
if git -C {{HOME}}/Code/kip-claw diff --cached --quiet; then
  CRON_NOTES="no changes"
  echo "[$TIMESTAMP] No pi health changes to commit" >> "$LOG"
else
  if ! git -C {{HOME}}/Code/kip-claw commit --no-verify -m "chore: update pi health data" >> "$LOG" 2>&1; then
    echo "[$TIMESTAMP] Failed: git commit for pi health data" >> "$LOG"
    CRON_NOTES="failed: commit"
    exit 1
  fi
  if ! timeout 120s git -C {{HOME}}/Code/kip-claw pull --rebase --autostash origin main >> "$LOG" 2>&1; then
    echo "[$TIMESTAMP] Failed: git pull --rebase for kip-claw" >> "$LOG"
    CRON_NOTES="failed: pull"
    exit 1
  fi
  if ! timeout 120s git -C {{HOME}}/Code/kip-claw push origin main >> "$LOG" 2>&1; then
    echo "[$TIMESTAMP] Failed: git push for kip-claw" >> "$LOG"
    CRON_NOTES="failed: push"
    exit 1
  fi
  CRON_NOTES="updated"
fi

echo "[$TIMESTAMP] Pi health logged — CPU: ${CPU_TEMP}°C, GPU: ${GPU_TEMP}°C, Load: ${LOAD1}" >> "$LOG"
