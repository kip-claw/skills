---
name: audiobook
description: Converts a long-form article, PDF, or web page into a narrated audiobook.
tag: Media
metadata: {"openclaw": {"emoji": "🎧"}}
---

# Audiobook

Use this skill when Kip asks to "make an audiobook of...", "narrate this article",
"read this aloud", or supplies a URL/PDF/EPUB and wants a long-form audio file
back. Default output is a single MP3 in `~/audiobooks/` with embedded ID3 tags
and (when supported by the container) chapter markers per section. Preserve that archival
copy, then stage a delivery copy under the shared workspace before attaching it to
Telegram or another channel. OpenClaw may reject media paths outside its allowed
attachment directories.

## Command

```bash
{{HOME}}/bin/article-audiobook-render.sh <url> [flags]
```

Direct invocation (equivalent):

```bash
python3 {{HOME}}/.openclaw/workspace/skills/audiobook/audiobook.py <url> [flags]
```

## Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--provider {openai,elevenlabs,speaches}` | from `config.yaml` | TTS backend |
| `--voice <name>` | `alloy` | Provider-specific voice id |
| `--speed <0.5-2.0>` | `1.0` | Speaking rate |
| `--format {mp3,m4a}` | `mp3` | Container; `m4a` enables real chapter markers |
| `--summary` | off | Summarize the article before narrating (uses default LLM) |
| `--podcast` | off | Add intro/outro narration |
| `--no-cache` | off | Skip per-chunk cache |
| `--dry-run` | off | Extract + chunk + print plan; do not call TTS |
| `--out <path>` | auto | Override the output path |

## Test example

```bash
{{HOME}}/bin/article-audiobook-render.sh \
  https://www.vatican.va/content/leo-xiv/en/encyclicals/documents/20260515-magnifica-humanitas.html
```

Expected stdout (one line per phase, ending with a JSON summary):

```text
fetch ok bytes=312841
extract ok title="Magnifica Humanitas" author="Pope Leo XIV" chars=158203
chunk ok sections=18 chunks=42 max_chars=3800
tts provider=openai voice=alloy chunks_total=42 cached=0 rendered=42
concat ok duration=05:12:47
tag ok format=mp3 path={{HOME}}/audiobooks/2026-05-30_magnifica-humanitas.mp3
{"title":"Magnifica Humanitas","author":"Pope Leo XIV","duration_seconds":18767,"runtime":"5h12m","path":"{{HOME}}/audiobooks/2026-05-30_magnifica-humanitas.mp3","chapters":18}
```

Reply to Kip with the human summary: `Generated audiobook for "<title>" by
<author>. Runtime: <h>h<m>m. File saved to <path>.` Also attach the staged
file per "Channel delivery" below — reporting the path in text alone does
not make it appear as a playable/downloadable attachment in any channel,
Control UI included.

## Caching

Per-chunk MP3 fragments are written to `~/.cache/openclaw-audiobook/<sha>.mp3`
where `<sha>` = `sha256(provider + voice + speed + chunk_text)`. Repeat runs of
the same URL with the same voice/speed only re-render chunks whose source text
actually changed. The cache is safe to delete at any time.

## Providers

Default and fallback order live in `config.yaml`. Provider credentials come
from `~/.openclaw/.env`:

- `OPENAI_API_KEY` — openai
- `ELEVENLABS_API_KEY` — elevenlabs
- `SPEACHES_BASE_URL` (default `http://latitude:8200`), `SPEACHES_TOKEN_FILE`
  (default `~/.config/openclaw-speaches/latitude-token`) — speaches (offline,
  self-hosted)

If the requested provider is unavailable, the script falls back to the next
provider in `provider.fallbacks`. Speaches is the offline fallback — it fills
the role Piper used to (no per-call API cost, works without internet), but
runs on Ben's Latitude laptop over Tailscale instead of locally on the Pi.

### Speaches (offline, self-hosted on Latitude)

- Server: `systemd --user` service `speaches.service` on Latitude, bound to
  `100.125.75.72:8200` (tailnet only, bearer-token auth, `/health` is the only
  public endpoint).
- Model: `speaches-ai/Kokoro-82M-v1.0-ONNX` — all 54 bundled voices are
  downloaded and available; default is `af_sky` (`providers.speaches.voice`
  in `config.yaml`).
- List voices: `curl -s http://latitude:8200/v1/models | jq '.data[].voices'`
  (requires the bearer token for anything except `/health`).
- Swap the default voice for a single run:
  ```bash
  ~/bin/article-audiobook-render.sh --provider speaches --voice af_heart <url>
  ```
- Cache keying includes the model + configured default voice, so changing
  `providers.speaches.voice` in `config.yaml` triggers a fresh render rather
  than returning a stale fragment; a `--voice` override on the CLI does too,
  since it's part of the chunk cache key.

## Source types

| Input | Extractor |
|-------|-----------|
| HTML page | `trafilatura` |
| PDF URL or `file://*.pdf` | `pypdf` |
| EPUB URL or `file://*.epub` | `ebooklib` + `BeautifulSoup` |
| Plain text URL | passthrough |
| Local Markdown/text file or `file://` URL | built-in plain-text extractor |

Local vault notes can be narrated directly:

```bash
{{HOME}}/bin/article-audiobook-render.sh "{{HOME}}/obsidian-vault/path/to/note.md" --format mp3
```

## Logs

Per-run JSONL log at `~/audiobooks/_log.jsonl`. Failed runs include the phase
that failed (`fetch|extract|chunk|tts|concat|tag`) plus the exception summary.

## Channel delivery

After a successful render, keep the tagged archival file in `~/audiobooks/`
and copy it to `{{HOME}}/.openclaw/workspace/tmp/audiobook-delivery/` before
attaching it to any channel — Telegram, Control UI, or otherwise. Two
independent reasons this staging step matters:

1. OpenClaw may reject local media paths outside its allowed directories, so
   staging under the workspace avoids that outright.
2. OpenClaw only renders a file as a chat attachment when the tool result
   carries the path in a structured field (`media`/`mediaUrl`/`path`/
   `filePath`) — never from the path merely being mentioned in reply text.
   Control UI specifically resolves *relative* media paths against the
   session's working directory (the agent workspace), so referencing the
   staged copy with a workspace-relative path is what lets it render, where
   an absolute `~/audiobooks/...` path may not.

Report the archival path (`~/audiobooks/...`) in the completion summary for
the human-readable record, but attach the staged workspace copy for the
actual delivery. Verify the staged copy exists before attempting to send.

**Known upstream caveat (as of OpenClaw 2026.9.4, 2026-09-17):** Control UI
had a real bug where relative media paths in tool replies weren't rendered
as attachments at all (`openclaw/openclaw#46240`), fixed upstream in
`openclaw/openclaw#147646` (merged 2026-09-14) — but not yet in any released
version as of 2026.9.4 (published 2026-09-11, predates the fix). If a
correctly-staged, correctly-referenced attachment still doesn't show up in
Control UI, check whether OpenClaw has shipped a release past this fix
before assuming the skill is broken.

## Errors and retries

- Network fetch: 3 retries with exponential backoff (handled by `httpx`)
- TTS request: 2 retries per chunk, then fall through to the next provider in
  the fallback chain for that chunk only (mixed-provider runs are allowed and
  logged)
- ffmpeg concat: fails fast — broken cache fragments are deleted and the run
  retries once

## RSS feed (nice-to-have)

If `rss.enabled: true` in `config.yaml`, every completed audiobook is appended
to `~/audiobooks/feed.xml` (Atom/Podcast-compatible). The feed is served by the
nginx tailnet vhost if `~/audiobooks/` is symlinked under the files site.

## When NOT to use this skill

- Short text (< 500 chars) — just narrate inline if needed.
- Paywalled or login-required URLs — extraction will fail; tell Kip.
- Copyrighted commercial books — out of scope; refuse.
