#!/bin/bash
# Usage: chartbeat-top-stories.sh <command> [args]
# Commands:
#   stories [limit] [host]       — top story pages only (excludes homepage and section fronts)
#   top [limit] [host]           — fetch top pages by concurrent visitors

set -euo pipefail

source {{HOME}}/.openclaw/.env

\1REDACTED
DEFAULT_HOST="reuters.com"

cmd="${1:-stories}"
if [[ $# -gt 0 ]]; then
  shift || true
fi

case "$cmd" in
  top|stories)
    limit="${1:-10}"
    host="${2:-$DEFAULT_HOST}"
    # Fetch extra results when filtering so we still return enough
    fetch_limit=$limit
    if [[ "$cmd" == "stories" ]]; then
      fetch_limit=$(( limit + 5 ))
    fi
    curl -sf "https://api.chartbeat.com/live/toppages/v3/?apikey=${API_KEY}&host=${host}&limit=${fetch_limit}" \
      | python3 -c "
import sys, json
cmd = '${cmd}'
limit = int('${limit}')
host = '${host}'
data = json.load(sys.stdin)
pages = data.get('pages', [])
if cmd == 'stories':
    pages = [p for p in pages if p.get('stats', {}).get('article', 0) > 0]
    pages = pages[:limit]
if not pages:
    print('No pages returned.')
    sys.exit(0)
for i, p in enumerate(pages, 1):
    title = p.get('title', '(no title)')
    path = p.get('path', '')
    if path.startswith('http://') or path.startswith('https://'):
        url = path
    elif path.startswith('//'):
        url = f'https:{path}'
    elif path.startswith(host + '/'):
        url = f'https://{path}'
    elif path.startswith('/'):
        url = f'https://{host}{path}'
    elif path:
        url = f'https://{host}/{path}'
    else:
        url = f'https://{host}/'
    people = p.get('stats', {}).get('people', 0)
    authors = ', '.join(p.get('authors', [])) or '—'
    sections = ', '.join(p.get('sections', [])) or '—'
    print(f'{i:>2}. [{people:,} readers] {title}')
    print(f'    {url}')
    print(f'    by {authors} | {sections}')
    print()
"
    ;;
  *)
    echo "Usage: chartbeat-top-stories.sh {stories|top} [limit] [host]"
    echo ""
    echo "Commands:"
    echo "  stories [limit] [host]  — top story pages only, excludes homepage and section fronts (default: 10, reuters.com)"
    echo "  top [limit] [host]      — top pages by concurrent visitors"
    exit 1
    ;;
esac
