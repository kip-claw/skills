#!/usr/bin/env bash
# Weekly disk-space cleanup for kip (Pi 4).
# Runs from the "Disk cleanup" OpenClaw cron job (isolated agent).
#
# Removes only caches and stale artifacts that regenerate on demand. Anything
# Kip might want to keep (final audiobook outputs are excluded except via the
# 14-day age cutoff) gets the gentlest possible treatment.
#
# Usage: system-disk-cleanup.sh [--dry-run]

set -euo pipefail

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
fi

LOG={{HOME}}/.cache/kip-disk-cleanup.log
mkdir -p "$(dirname "$LOG")"

note() { printf '%s %s\n' "$(date -Iseconds)" "$*" | tee -a "$LOG"; }
do_rm() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    note "DRY-RUN would: $*"
  else
    eval "$@"
  fi
}

before_kb=$(df -Pk / | awk 'NR==2 {print $3}')
note "=== kip-disk-cleanup start (dry_run=$DRY_RUN) used_kb=$before_kb ==="

# 1. apt archive cache
do_rm "sudo -n apt clean 2>/dev/null || true"

# 2. npm caches (user + root)
do_rm "rm -rf {{HOME}}/.npm/_cacache {{HOME}}/.npm/_logs"
do_rm "sudo -n rm -rf /root/.npm/_cacache /root/.npm/_logs 2>/dev/null || true"

# 3. build/install caches
do_rm "rm -rf {{HOME}}/.cache/node-gyp {{HOME}}/.cache/pip"

# 4. tombstoned OpenClaw session files
do_rm "find {{HOME}}/.openclaw/agents/main/sessions -name '*.deleted.*' -delete 2>/dev/null || true"

# 4b. OpenClaw session trajectories older than 30 days
do_rm "find {{HOME}}/.openclaw/agents/main/sessions -name '*.trajectory.jsonl' -mtime +30 -delete 2>/dev/null || true"

# 4c. codex-home npm download cache (regenerates on demand)
do_rm "rm -rf {{HOME}}/.openclaw/agents/main/agent/codex-home/home/.npm/_cacache {{HOME}}/.openclaw/agents/main/agent/codex-home/home/.npm/_logs"

# 4d. pnpm: drop packages not referenced by any project, plus stale cache metadata
do_rm "pnpm store prune 2>/dev/null || true"

# 4e. OpenClaw compile cache (/var/tmp)
do_rm "sudo -n rm -rf /var/tmp/openclaw-compile-cache/* 2>/dev/null || rm -rf /var/tmp/openclaw-compile-cache/* 2>/dev/null || true"

# 4f. systemd journal — cap retained logs at 50M
do_rm "sudo -n journalctl --vacuum-size=50M 2>/dev/null || true"

# 5. old VS Code server installs — keep the two most recently used
if [[ -d {{HOME}}/.vscode-server/cli/servers ]]; then
  mapfile -t old_servers < <(
    cd {{HOME}}/.vscode-server/cli/servers && \
    ls -1dt Stable-* 2>/dev/null | tail -n +3
  )
  for d in "${old_servers[@]:-}"; do
    [[ -z "$d" ]] && continue
    do_rm "rm -rf '{{HOME}}/.vscode-server/cli/servers/$d'"
  done
fi

# Audiobook outputs and chunk cache are pruned by HEARTBEAT.md (3-day cutoff,
# runs more often than this weekly cron). Don't duplicate the policy here.

after_kb=$(df -Pk / | awk 'NR==2 {print $3}')
freed_kb=$(( before_kb - after_kb ))
freed_mb=$(( freed_kb / 1024 ))
df_line=$(df -h / | tail -1)

note "df after: $df_line"
note "=== kip-disk-cleanup done freed_mb=$freed_mb ==="

echo "freed_mb=$freed_mb"
echo "df: $df_line"
