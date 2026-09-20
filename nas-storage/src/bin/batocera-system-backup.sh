#!/bin/bash
# Backs up Batocera to NAS via Kip as intermediary
set -uo pipefail

SCRIPT_START=$(date +%s)
trap 'DURATION=$(( $(date +%s) - SCRIPT_START )); bash {{HOME}}/bin/kip-cron-log.sh "kip-batocera-backup" "$?" "$DURATION" ""' EXIT

NAS_BASE="kip-nas:/srv/dev-disk-by-uuid-a170c673-36d0-4a82-a615-e7356ef68cc6/Backups/batocera"
BAT_HOST="root@100.97.0.64"
BAT_OPTS="-i {{HOME}}/.ssh/batocera_key -o ConnectTimeout=10 -o StrictHostKeyChecking=no -o BatchMode=yes"
NAS_OPTS="-i {{HOME}}/.ssh/nas_key -o ConnectTimeout=10 -o StrictHostKeyChecking=no"
STAGING="/tmp/batocera-backup"
LOG="/var/log/kip-batocera-backup.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$DATE] Starting Batocera backup" >> "$LOG"

backup_dir() {
  local src="$1"
  local dst="$2"
  local staging="$STAGING/$dst"

  # Check if directory exists on Batocera first
  if ssh $BAT_OPTS "$BAT_HOST" "test -d $src" 2>/dev/null; then
    :
  else
    local check_status=$?
    if [ "$check_status" -eq 1 ]; then
      echo "[$DATE] SKIP: $src (not found)" >> "$LOG"
      return 0
    fi
    echo "[$DATE] FAILED source check: $src (SSH status $check_status)" >> "$LOG"
    return 1
  fi

  mkdir -p "$staging"

  rsync -az --delete \
    -e "ssh $BAT_OPTS" \
    "$BAT_HOST:$src" \
    "$staging" >> "$LOG" 2>&1

  if [ $? -ne 0 ]; then
    echo "[$DATE] FAILED pull: $src" >> "$LOG"
    return 1
  fi

  rsync -az --delete \
    -e "ssh $NAS_OPTS" \
    "$staging" \
    "$NAS_BASE/$dst" >> "$LOG" 2>&1

  if [ $? -eq 0 ]; then
    echo "[$DATE] OK: $src" >> "$LOG"
  else
    echo "[$DATE] FAILED push: $src" >> "$LOG"
  fi
}

FAILED=0
backup_dir "/userdata/saves/"       "saves/"       || FAILED=1
backup_dir "/userdata/states/"      "states/"      || FAILED=1
backup_dir "/userdata/system/"      "system/"      || FAILED=1
backup_dir "/userdata/screenshots/" "screenshots/" || FAILED=1
backup_dir "/userdata/gamelists/"   "gamelists/"   || FAILED=1
backup_dir "/userdata/themes/"      "themes/"      || FAILED=1
backup_dir "/userdata/cheats/"      "cheats/"      || FAILED=1

rm -rf "$STAGING"
if [ "$FAILED" -ne 0 ]; then
  echo "[$DATE] Batocera backup FAILED" >> "$LOG"
  exit 1
fi
echo "[$DATE] Batocera backup complete" >> "$LOG"
