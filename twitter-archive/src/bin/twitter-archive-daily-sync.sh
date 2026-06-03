#!/bin/bash
# twitter-archive-sync.sh — Daily sync of @palewire Twitter activity
# Ensures comprehensive collection of all authored tweets and media.
#
# Strategy:
# 1. Ingest authored tweets via bird user-tweets → SQLite (free, cookie-based)
# 2. Sync mentions via birdclaw sync mentions (captures replies to us)
# 3. Sync mention threads (conversation context)
# 4. Fetch new media for any tweets added
# 5. Export canonical JSONL backup shards (consumed by twitter-archive-data-export.sh)
# Offsite backup handled by NAS rclone-r2-sync.sh (covers entire Data dir)

SCRIPT_START=$(date +%s)
trap 'DURATION=$(( $(date +%s) - SCRIPT_START )); bash {{HOME}}/bin/kip-cron-log.sh "kip-birdclaw-sync" "$?" "$DURATION" "${CRON_NOTES:-}"' EXIT

SSH_OPTS="-i {{HOME}}/.ssh/nas_key -o ConnectTimeout=10 -o StrictHostKeyChecking=no"
NAS_SSH_TARGET="nas@100.118.154.80"
WRAPPER="/home/nas/bin/birdclaw-wrapper.sh"
LOG="{{HOME}}/.openclaw/logs/kip-birdclaw-sync.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

mkdir -p "$(dirname "$LOG")"
echo "[$DATE] Starting birdclaw sync" >> "$LOG"

# --- Step 1: Ingest authored tweets via bird user-tweets → SQLite ---
echo "[$DATE] Ingesting authored tweets..." >> "$LOG"
INGEST_RESULT=$(ssh $SSH_OPTS "$NAS_SSH_TARGET" "/home/nas/bin/birdclaw-ingest-authored.sh" 2>&1)
INGEST_EXIT=$?
if [ $INGEST_EXIT -eq 0 ]; then
  echo "[$DATE] Authored ingest OK: $INGEST_RESULT" >> "$LOG"
else
  echo "[$DATE] Authored ingest failed (exit $INGEST_EXIT): $INGEST_RESULT" >> "$LOG"
fi

# --- Step 2: Sync mentions (captures replies to us) ---
echo "[$DATE] Syncing mentions..." >> "$LOG"
MENTIONS_RESULT=$(ssh $SSH_OPTS "$NAS_SSH_TARGET" "$WRAPPER sync mentions --mode bird --limit 100 --max-pages 5 --json" 2>&1)
if [ $? -eq 0 ]; then
  MENTIONS_COUNT=$(echo "$MENTIONS_RESULT" | python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(d.get('count',0))" 2>/dev/null || echo "?")
  echo "[$DATE] Mentions sync OK: $MENTIONS_COUNT new" >> "$LOG"
else
  echo "[$DATE] Mentions sync failed" >> "$LOG"
  MENTIONS_COUNT="err"
fi

# --- Step 3: Sync mention threads (conversation context) ---
echo "[$DATE] Syncing mention threads..." >> "$LOG"
THREADS_RESULT=$(ssh $SSH_OPTS "$NAS_SSH_TARGET" "$WRAPPER sync mention-threads --mode bird --limit 30 --json" 2>&1)
if [ $? -eq 0 ]; then
  echo "[$DATE] Mention threads OK" >> "$LOG"
else
  echo "[$DATE] Mention threads failed" >> "$LOG"
fi

# --- Step 4: Fetch media for any new tweets ---
echo "[$DATE] Fetching media..." >> "$LOG"
MEDIA_RESULT=$(ssh $SSH_OPTS "$NAS_SSH_TARGET" "$WRAPPER media fetch --parallel 3 --pacing-ms 500 --include-video --json" 2>&1)
if [ $? -eq 0 ]; then
  MEDIA_COUNT=$(echo "$MEDIA_RESULT" | python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(f\"fetched={d.get('fetched',0)} cached={d.get('skipped_cached',0)}\")" 2>/dev/null || echo "?")
  echo "[$DATE] Media fetch OK: $MEDIA_COUNT" >> "$LOG"
else
  echo "[$DATE] Media fetch failed" >> "$LOG"
  MEDIA_COUNT="err"
fi

# --- Step 5: Export canonical JSONL backup shards ---
# The kip-twitter-export.py downstream consumer reads these JSONL files via SSH.
# Without this step the JSONLs go stale and the kip-claw export becomes a no-op.
echo "[$DATE] Exporting backup..." >> "$LOG"
BACKUP_REPO="/srv/dev-disk-by-uuid-a170c673-36d0-4a82-a615-e7356ef68cc6/Data/birdclaw/backup"
EXPORT_RESULT=$(ssh $SSH_OPTS "$NAS_SSH_TARGET" "$WRAPPER backup export --repo $BACKUP_REPO" 2>&1)
if [ $? -eq 0 ]; then
  echo "[$DATE] Backup export OK" >> "$LOG"
else
  echo "[$DATE] Backup export failed: $EXPORT_RESULT" >> "$LOG"
fi

# --- Summary ---
CRON_NOTES="authored=${INGEST_RESULT##*: } mentions=$MENTIONS_COUNT media=$MEDIA_COUNT"
echo "[$DATE] Sync complete: $CRON_NOTES" >> "$LOG"
