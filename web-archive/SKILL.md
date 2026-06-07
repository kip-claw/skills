---
name: web-archive
description: >
  Archives a URL to the local ArchiveBox instance on the NAS. Use when the
  user asks to "save", "archive", "preserve", or "capture" a web page or
  URL. Also use when saving sources, references, or articles for later.
---

# Web Archive

To archive a URL to the local NAS archive:

Run: `{{HOME}}/bin/kip-archive.sh <url> [optional-tag]`

Examples:
- `{{HOME}}/bin/kip-archive.sh https://example.com/article`
- `{{HOME}}/bin/kip-archive.sh https://example.com/article reuters`

Tags are optional but useful for organizing by topic or story.

The archive web UI is accessible at https://archive.kip.computer

ArchiveBox saves: HTML snapshot, PDF, screenshot, WARC, article text
(readability), and media where applicable. Some sites block scrapers so
partial captures are normal — the singlefile HTML snapshot is the most
reliable extractor.

If the script fails or SSH times out, the NAS may be unreachable — check
Tailscale and confirm the archivebox container is running:
`ssh kip-nas "docker ps | grep archivebox"`

Notify the user via Telegram with a confirmation once the URL is queued,
and include a link to https://archive.kip.computer
