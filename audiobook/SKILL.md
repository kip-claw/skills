---
name: audiobook
description: Convert a long-form article, essay, speech, blog post, PDF, or public document URL into a narrated MP3/M4A audiobook using a pluggable TTS provider (OpenAI / ElevenLabs / Piper / Kokoro). Caches per-chunk audio so repeated runs only re-render changed sections.
metadata: {"openclaw": {"emoji": "🎧"}}
---

# Audiobook

Use this skill when Kip asks to "make an audiobook of...", "narrate this article",
"read this aloud", or supplies a URL/PDF/EPUB and wants a long-form audio file
back. Default output is a single MP3 in `~/audiobooks/` with embedded ID3 tags
and (when supported by the container) chapter markers per section.

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
| `--provider {openai,elevenlabs,piper,kokoro}` | from `config.yaml` | TTS backend |
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
<author>. Runtime: <h>h<m>m. File saved to <path>.`

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
- `PIPER_BIN` (path), `PIPER_VOICE` (model path) — piper (offline)
- `KOKORO_BIN`, `KOKORO_VOICE` — kokoro (offline)

If the requested provider is unavailable, the script falls back to the next
provider in `provider.fallbacks`. Piper is the recommended offline fallback on
the Pi (CPU only, ~1×realtime on a Pi 4).

### Piper (offline, installed on kip)

- Binary: `{{HOME}}/.local/bin/piper` (Python package `piper-tts` v1.4.2)
- Models live in `{{HOME}}/.local/share/piper/` — one `.onnx` + matching `.onnx.json`
- Default voice (from `~/.openclaw/.env` → `PIPER_VOICE`): `en_US-amy-medium.onnx`
- Currently installed voices on kip:
  - `en_US-amy-medium.onnx` — warm female, default
  - `en_US-hfc_male-medium.onnx` — Home Assistant Cloud male, neutral news read
  - `en_US-ryan-high.onnx` — clear male, highest quality (~2-3× slower on Pi)
- Swap voices for a single run by exporting `PIPER_VOICE` inline:
  ```bash
  PIPER_VOICE={{HOME}}/.local/share/piper/en_US-hfc_male-medium.onnx \
    ~/bin/article-audiobook-render.sh --provider piper <url>
  ```
- More voices: download `<name>.onnx` + `<name>.onnx.json` from
  https://huggingface.co/rhasspy/piper-voices into `~/.local/share/piper/`.
  Browse `en/en_US/<voice>/<quality>/` (qualities: `low`, `medium`, `high`).
- Cache keying respects the resolved voice file path, so swapping `PIPER_VOICE`
  triggers a fresh render rather than returning a stale fragment.

## Source types

| Input | Extractor |
|-------|-----------|
| HTML page | `trafilatura` |
| PDF URL or `file://*.pdf` | `pypdf` |
| EPUB URL or `file://*.epub` | `ebooklib` + `BeautifulSoup` |
| Plain text URL | passthrough |

## Logs

Per-run JSONL log at `~/audiobooks/_log.jsonl`. Failed runs include the phase
that failed (`fetch|extract|chunk|tts|concat|tag`) plus the exception summary.

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
