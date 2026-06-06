#!/bin/bash
# Usage: nas-storage-operations.sh <command> [args]
# Commands:
#   status          — disk usage summary
#   list [path]     — list directory contents
#   push <src> <dst> — rsync local file/dir to NAS
#   pull <src> <dst> — rsync NAS file/dir to local
#   health          — SMART health check on all drives
#   inspect-device  — temporarily mount a device read-only and list contents
#   device-inventory — show NAS block devices and OMV filesystem registry
#   summarize [path] — summarize a NAS path with sizes and file samples
#   archive-mounted <source> <dest> [--dry-run] — rsync one mounted NAS path into another
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
  inspect-device)
    device="${1:-/dev/sdc}"
    ssh $SSH_OPTS kip-nas 'bash -s' -- "$device" <<'EOF'
set -euo pipefail

device="$1"
if [ ! -b "$device" ]; then
  echo "ERROR: $device is not a block device."
  exit 1
fi

echo "== Block devices =="
lsblk -o NAME,PATH,SIZE,FSTYPE,LABEL,UUID,MOUNTPOINTS "$device"
echo

echo "== Filesystem metadata =="
if ! blkid "$device" 2>/dev/null; then
  blkid "${device}"?* 2>/dev/null || echo "blkid unavailable without elevated privileges; using lsblk metadata above."
fi
echo

mapfile -t targets < <(lsblk -nrpo PATH,TYPE "$device" | awk '$2 == "part" {print $1}')
if [ "${#targets[@]}" -eq 0 ]; then
  targets=("$device")
fi

for target in "${targets[@]}"; do
  fstype="$(lsblk -nrpo FSTYPE "$target" | head -1)"
  if [ -z "$fstype" ]; then
    echo "== $target =="
    echo "No filesystem detected; skipping mount."
    echo
    continue
  fi

  mountpoint="/tmp/openclaw-inspect-$(basename "$target")"
  mkdir -p "$mountpoint"

  already_mounted="$(lsblk -nrpo MOUNTPOINTS "$target" | head -1)"
  mounted_here=0
  if [ -n "$already_mounted" ]; then
    mountpoint="$already_mounted"
  else
    if sudo -n mount -o ro,noload "$target" "$mountpoint" 2>/dev/null; then
      mounted_here=1
    elif sudo -n mount -o ro "$target" "$mountpoint"; then
      mounted_here=1
    elif command -v udisksctl >/dev/null 2>&1 && udisksctl mount -b "$target" --options ro >/tmp/openclaw-udisksctl.out 2>/tmp/openclaw-udisksctl.err; then
      mountpoint="$(lsblk -nrpo MOUNTPOINTS "$target" | head -1)"
      mounted_here=2
    else
      echo "== $target =="
      echo "Mount failed."
      if [ -s /tmp/openclaw-udisksctl.err ]; then
        sed 's/^/udisksctl: /' /tmp/openclaw-udisksctl.err
      fi
      echo
      continue
    fi
  fi

  echo "== $target mounted at $mountpoint =="
  echo "-- Top level --"
  find "$mountpoint" -maxdepth 1 -mindepth 1 -printf '%M %10s %TY-%Tm-%Td %TH:%TM %p\n' | sort | head -100
  echo
  echo "-- Two-level directory sample --"
  find "$mountpoint" -maxdepth 2 -type d -printf '%p\n' | sort | head -100
  echo

  if [ "$mounted_here" -eq 1 ]; then
    sudo -n umount "$mountpoint"
    rmdir "$mountpoint" 2>/dev/null || true
    echo "Unmounted temporary read-only mount for $target."
    echo
  elif [ "$mounted_here" -eq 2 ]; then
    udisksctl unmount -b "$target" >/dev/null 2>&1 || true
    echo "Unmounted temporary read-only udisks mount for $target."
    echo
  fi
done
EOF
    ;;
  device-inventory)
    ssh $SSH_OPTS kip-nas 'bash -s' <<'EOF'
set -euo pipefail

echo "== lsblk =="
lsblk -o NAME,PATH,SIZE,TYPE,FSTYPE,LABEL,UUID,MOUNTPOINTS
echo

echo "== findmnt /srv =="
findmnt /srv || true
echo

echo "== OMV filesystem registry =="
if command -v omv-confdbadm >/dev/null 2>&1; then
  omv-confdbadm read conf.system.filesystem.mountpoint 2>/dev/null || true
else
  echo "omv-confdbadm not found."
fi
EOF
    ;;
  summarize)
    path="${1:-$NAS_MOUNT}"
    ssh $SSH_OPTS kip-nas 'bash -s' -- "$path" <<'EOF'
set -euo pipefail
path="$1"

if [ ! -e "$path" ]; then
  echo "ERROR: path not found: $path"
  exit 1
fi

echo "== Path =="
printf '%s\n\n' "$path"

echo "== Disk usage =="
df -h "$path"
echo

echo "== Top-level sizes =="
du -h --max-depth=1 "$path" 2>/dev/null | sort -h
echo

echo "== Top-level listing =="
find "$path" -maxdepth 1 -mindepth 1 -printf '%M %10s %TY-%Tm-%Td %TH:%TM %p\n' | sort | head -200
echo

echo "== Directory sample =="
find "$path" -maxdepth 3 -type d -printf '%p\n' | sort | head -200
echo

echo "== File sample =="
find "$path" -maxdepth 3 -type f -printf '%s\t%TY-%Tm-%Td %TH:%TM\t%p\n' | sort -nr | head -100
EOF
    ;;
  archive-mounted)
    source="${1:?source path required}"
    dest="${2:?destination path required}"
    mode="${3:-}"
    ssh $SSH_OPTS kip-nas 'bash -s' -- "$source" "$dest" "$mode" <<'EOF'
set -euo pipefail
source="$1"
dest="$2"
mode="${3:-}"

if [ ! -d "$source" ]; then
  echo "ERROR: source directory not found: $source"
  exit 1
fi

case "$dest" in
  /srv/dev-disk-by-uuid-a170c673-36d0-4a82-a615-e7356ef68cc6/*) ;;
  *)
    echo "ERROR: destination must be on the primary WD NAS drive."
    exit 1
    ;;
esac

mkdir -p "$dest"

args=(-a --human-readable --info=stats2,progress2 --exclude='/lost+found/')
if [ "$mode" = "--dry-run" ]; then
  args+=(--dry-run)
fi

rsync "${args[@]}" "$source"/ "$dest"/
EOF
    ;;
  sync)
    ssh $SSH_OPTS kip-nas "/home/nas/bin/rclone-sync.sh"
    ;;
  r2-sync)
    ssh $SSH_OPTS kip-nas "/home/nas/bin/rclone-r2-sync.sh"
    ;;
  *)
    echo "Usage: nas-storage-operations.sh {status|list|push|pull|health|inspect-device|device-inventory|summarize|archive-mounted|sync|r2-sync} [args]"
    exit 1
    ;;
esac
