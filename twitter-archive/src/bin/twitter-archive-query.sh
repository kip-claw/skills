#!/bin/bash
# Usage: twitter-archive-cli.sh <birdclaw-command> [args...]
# Runs birdclaw on the NAS via SSH, passing all arguments through.
# Examples:
#   twitter-archive-cli.sh search tweets "journalism" --limit 20 --json
#   twitter-archive-cli.sh db stats --json
#   twitter-archive-cli.sh digest week --json
#   twitter-archive-cli.sh today

SSH_OPTS="-i {{HOME}}/.ssh/nas_key -o ConnectTimeout=5 -o StrictHostKeyChecking=no"
NAS_SSH_TARGET="nas@100.118.154.80"
WRAPPER="/home/nas/bin/birdclaw-wrapper.sh"

if [ $# -eq 0 ]; then
  echo "Usage: twitter-archive-cli.sh <birdclaw-command> [args...]"
  echo ""
  echo "Commands:"
  echo "  search tweets <query> [--limit N] [--json]"
  echo "  search tweets --liked [--limit N] [--json]"
  echo "  search tweets --bookmarked [--limit N] [--json]"
  echo "  search dms <query> [--limit N] [--json]"
  echo "  db stats [--json]"
  echo "  today"
  echo "  digest week [--json]"
  echo "  backup export --repo <path> [--commit] [--json]"
  exit 1
fi

# Escape arguments for remote shell
ESCAPED_ARGS=""
for arg in "$@"; do
  ESCAPED_ARGS="$ESCAPED_ARGS '$(echo "$arg" | sed "s/'/'\\\\''/g")'"
done

exec ssh $SSH_OPTS "$NAS_SSH_TARGET" "$WRAPPER $ESCAPED_ARGS"
