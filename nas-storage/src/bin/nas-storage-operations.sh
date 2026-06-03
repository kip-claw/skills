#!/bin/bash
# Usage: nas-storage-operations.sh <command> [args]
# Commands:
#   status          — disk usage summary
#   list [path]     — list directory contents
#   push <src> <dst> — rsync local file/dir to NAS
#   pull <src> <dst> — rsync NAS file/dir to local
#   health          — SMART health check on all drives
#   sync            — sync Google Drive to NAS via rclone
#   r2-sync         — offsite backup of NAS to Cloudflare R2

NAS_MOUNT="/srv/dev-disk-by-uuid-a170c673-36d0-4a82-a615-e7356ef68cc6"
SSH_OPTS="-i {{HOME}}/.ssh/nas_key -o ConnectTimeout=5 -o StrictHostKeyChecking=no"

cmd="$1"
shift

case "$cmd" in
  status)
    ssh $SSH_OPTS kip-nas "df -h $NAS_MOUNT"
    ;;
  list)
    path="${1:-$NAS_MOUNT}"
    ssh $SSH_OPTS kip-nas "ls -lh $path"
    ;;
  push)
    rsync -avz -e "ssh $SSH_OPTS" "$1" "kip-nas:$NAS_MOUNT/${2:-}"
    ;;
  pull)
    rsync -avz -e "ssh $SSH_OPTS" "kip-nas:$NAS_MOUNT/$1" "${2:-.}"
    ;;
  health)
    ssh $SSH_OPTS kip-nas 'bash -s' <<'EOF'
SMARTCTL_BIN=""
for candidate in smartctl /usr/sbin/smartctl /usr/local/sbin/smartctl /usr/bin/smartctl; do
  if [ "${candidate#/}" != "$candidate" ]; then
    if [ -x "$candidate" ]; then
      SMARTCTL_BIN="$candidate"
      break
    fi
  elif command -v "$candidate" >/dev/null 2>&1; then
    SMARTCTL_BIN="$(command -v "$candidate")"
    break
  fi
done

if [ -z "$SMARTCTL_BIN" ]; then
  echo "SMART_UNAVAILABLE: smartctl is not installed on NAS (install smartmontools)."
  exit 0
fi

if ! sudo -n "$SMARTCTL_BIN" --version >/dev/null 2>&1; then
  echo "SMART_UNAVAILABLE: sudo requires a password for NAS user; cannot run smartctl non-interactively."
  echo "TIP: allow passwordless sudo for smartctl, or run SMART checks manually on NAS."
  exit 0
fi

for d in /dev/sd?; do
  [ -b "$d" ] || continue
  echo "--- $d"
  success=0
  for t in auto sat scsi; do
    out=$(sudo -n "$SMARTCTL_BIN" -H -d "$t" "$d" 2>&1)
    rc=$?
    if [ $rc -eq 0 ]; then
      echo "$out" | sed "s/^/[${t}] /"
      success=1
      break
    fi
  done
  if [ $success -eq 0 ]; then
    echo "SMART_UNAVAILABLE: no working smartctl transport for $d (tried auto,sat,scsi)."
  fi
done
EOF
    ;;
  sync)
    ssh $SSH_OPTS kip-nas "/home/nas/bin/rclone-sync.sh"
    ;;
  r2-sync)
    ssh $SSH_OPTS kip-nas "/home/nas/bin/rclone-r2-sync.sh"
    ;;
  *)
    echo "Usage: nas-storage-operations.sh {status|list|push|pull|health|sync|r2-sync} [args]"
    exit 1
    ;;
esac
