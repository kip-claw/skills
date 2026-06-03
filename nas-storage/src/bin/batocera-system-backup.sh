#!/bin/bash
# Backs up Batocera to NAS via Kip as intermediary
SCRIPT_START=$(date +%s)
trap 'DURATION=$(( $(date +%s) - SCRIPT_START )); bash {{HOME}}/bin/kip-cron-log.sh "kip-batocera-backup" "$?" "$DURATION" ""' EXIT

NAS_BASE="kip-nas:/srv/dev-disk-by-uuid-a170c673-36d0-4a82-a615-e7356ef68cc6/Backups/batocera"
BAT_OPTS="-i {{HOME}}/.ssh/batocera_key -o ConnectTimeout=10 -o StrictHostKeyChecking=no"
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
  ssh $BAT_OPTS root@batocera "test -d $src" 2>/dev/null
  if [ $? -ne 0 ]; then
    echo "[$DATE] SKIP: $src (not found)" >> "$LOG"
    return 0
  fi

  mkdir -p "$staging"

  rsync -az --delete \
    -e "ssh $BAT_OPTS" \
    "root@batocera:$src" \
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

backup_dir "/userdata/saves/"       "saves/"
backup_dir "/userdata/states/"      "states/"
backup_dir "/userdata/system/"      "system/"
backup_dir "/userdata/screenshots/" "screenshots/"
backup_dir "/userdata/gamelists/"   "gamelists/"
backup_dir "/userdata/themes/"      "themes/"
backup_dir "/userdata/cheats/"      "cheats/"

rm -rf "$STAGING"
echo "[$DATE] Batocera backup complete" >> "$LOG"
