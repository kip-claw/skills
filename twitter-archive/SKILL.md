---
name: twitter-archive
description: Searches Ben's @palewire Twitter archive of tweets, likes, and messages.
tag: Media
---

# Twitter Archive

Ben's full Twitter/X archive for @palewire is stored and indexed on the NAS
using [birdclaw](https://birdclaw.sh/). The archive includes tweets, likes,
bookmarks, DMs, profiles, and follower/following edges going back over a decade.

All queries run via SSH to the NAS. Use `{{HOME}}/bin/twitter-archive-cli.sh`.

## Commands

**Search tweets (FTS5 full-text search):**
```bash
{{HOME}}/bin/twitter-archive-cli.sh search tweets "query" --limit 20 --json
```

**Search liked tweets:**
```bash
{{HOME}}/bin/twitter-archive-cli.sh search tweets --liked --limit 20 --json
```

**Search bookmarked tweets:**
```bash
{{HOME}}/bin/twitter-archive-cli.sh search tweets --bookmarked --limit 20 --json
```

**Search DMs:**
```bash
{{HOME}}/bin/twitter-archive-cli.sh search dms "query" --limit 20 --json
```

**Daily digest (streaming summary of recent activity):**
```bash
{{HOME}}/bin/twitter-archive-cli.sh today
{{HOME}}/bin/twitter-archive-cli.sh digest week --json
```

**Database stats:**
```bash
{{HOME}}/bin/twitter-archive-cli.sh db stats --json
```

**Follower graph:**
```bash
{{HOME}}/bin/twitter-archive-cli.sh graph summary --json
{{HOME}}/bin/twitter-archive-cli.sh graph mutuals --limit 50 --json
{{HOME}}/bin/twitter-archive-cli.sh graph top-followers --limit 20 --json
```

## Architecture

- **Data location:** NAS at `/srv/.../Data/birdclaw/`
  - `birdclaw.sqlite` — canonical SQLite database with FTS5 indexes
  - `media/originals/` — extracted images/video from the archive
  - `archive/` — original ZIP download(s)
- **Runtime:** Node 25.9.0 via fnm on the NAS
- **Wrapper:** `/home/nas/bin/birdclaw-wrapper.sh` (sets PATH + BIRDCLAW_HOME)
- **Backup:** JSONL shards via `birdclaw backup export`, picked up by existing NAS → R2 offsite sync

## Backup

To export a Git-friendly JSONL backup:
```bash
{{HOME}}/bin/twitter-archive-cli.sh backup export --repo /srv/dev-disk-by-uuid-a170c673-36d0-4a82-a615-e7356ef68cc6/Data/birdclaw/backup --commit --json
```

This is included in the existing `r2-sync` offsite backup automatically.

## Kip-Claw Export

A daily cron job exports a summary JSON for the kip-claw Twitter archive page:

- **Cron:** `Twitter archive export` — runs daily at 6:00 AM ET (after sync at 5:30 AM)
- **Wrapper:** `{{HOME}}/bin/twitter-archive-data-export.sh`
- **Script:** `{{HOME}}/bin/twitter-archive-export-core.py <json_path>`
- **Output:** `{{HOME}}/kip-claw/static/data/twitterArchive.json`
- **Commits** changes to kip-claw and pushes to deploy

The export reads from the NAS backup (`data/timeline_edges/authored.jsonl` + `data/tweets/*.jsonl`)
and produces summary stats, monthly tweet counts, and top 10 tweets by likes.

## Re-importing

If a newer archive is downloaded, transfer it to the NAS and re-import:
```bash
{{HOME}}/bin/nas-storage-operations.sh push ~/Downloads/twitter-*.zip Data/birdclaw/archive/
{{HOME}}/bin/twitter-archive-cli.sh import archive /srv/dev-disk-by-uuid-a170c673-36d0-4a82-a615-e7356ef68cc6/Data/birdclaw/archive/<filename>.zip --json
```

Selective re-import (e.g., only refresh tweets, keep live likes):
```bash
{{HOME}}/bin/twitter-archive-cli.sh import archive <path>.zip --select tweets --json
```

## Notes

- The NAS must be reachable over Tailscale for any command to work
- `--json` flag gives structured output; omit it for human-readable text
- `today` and `digest` require OPENAI_API_KEY for AI summaries (optional)
- Without a live transport (xurl/bird), birdclaw operates in archive-only mode — searches work, live sync does not
- Archive account: @palewire

## Publish Decision

This is a publish candidate after sanitizing:
- Remove NAS paths and UUIDs
- Keep command patterns generic
