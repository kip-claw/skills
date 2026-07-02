---
name: "reuters-news-bosch"
description: Generates Bosch-inspired editorial images from Reuters' most-read stories.
tag: Work
---

# Reuters News Bosch

Generate a daily news allegory from Reuters Chartbeat's most-read stories,
publish it to the public site, and deliver the live link to Telegram. The
entire pipeline is deterministic and runs unattended from a single orchestrator
script. Generation, publishing, and delivery are fully automated end to end;
no step requires human review or model calls beyond theme derivation.

## Generate

The whole generation pipeline runs from one allowlisted orchestrator:

```bash
{{HOME}}/bin/reuters-news-bosch-cron.sh
```

It performs these discrete, individually testable steps and writes everything
into a dated run directory under
`${HOME}/.openclaw/workspace/tmp/reuters-news-bosch/`:

1. `scripts/chartbeat_snapshot.py --limit 10` — immutable ranked source
   snapshot (`chartbeat.json`). Stops if fewer than five suitable stories.
2. `scripts/direction_card.py --date <today> --runs-root <root>` — deterministic,
   date-seeded creative direction (`direction.json`), including
   `avoidRecentMotifs` derived from recent manifests.
3. `scripts/derive_themes.py` — derives 3-6 themes (`themes.json`) plus a
   `themes-meta.json` sidecar. Themes come from the **configured default model**
   via `openclaw infer model run --json` (no `--model`, so it follows config).
   The response is strictly validated: every theme must cite at least one real
   story rank. If the model is throttled, unavailable, or returns invalid output,
   it falls back to a **deterministic, content-aware rule-based deriver** so the
   edition always ships. `themeSource` records `model` or `fallback`.
4. `scripts/compose_edition.py` — deterministic assembly of `prompt.txt`,
   `alt.txt`, and `caption.md` from the snapshot, direction card, and themes.
   The prompt builds a panoramic three-part allegory (left: origins/causes;
   center: the central conflict; right: aftermath/risks), honors the direction
   card, avoids `avoidRecentMotifs`, and instructs the model to invent a fresh
   symbolic vocabulary.
5. Image generation — `openclaw infer image generate --model openai/gpt-image-2`
   (OpenAI only, `--size 1536x1024`, `--timeout-ms 900000`) with up to three
   retries. `scripts/select_image.py` normalizes the output to `image.png` and
   fails hard on an empty or missing image.
5c. `scripts/validate_image.py` — deterministic image sanity gate that replaces
   the old human review for mechanical failures. Rejects an unreadable,
   wrongly-shaped (non-landscape, e.g. a 1:1 fallback), truncated, or near-blank
   frame before any manifest build or publish. No model calls.
6. `scripts/build_manifest.py --meta-file themes-meta.json` — writes
   `manifest.json` (provenance, `themeSource`, `motifsUsed`) and `preview.md`.
   Recording `motifsUsed` re-enables motif repetition control for future runs.
7. `scripts/publish_to_site.py --publish` — deterministic, unattended publish
   of the edition to the public site (see **Publish** below). No model calls.
8. Telegram delivery — sends the live page link and the image once publishing
   has fully finished. On any failure the orchestrator sends a concise Telegram
   failure notice and logs to
   `${HOME}/.openclaw/logs/kip-reuters-news-bosch.log`.
9. Housekeeping — best-effort pruning of run directories (keeps the most recent
   30) and rotation of the log once it exceeds 5 MB. Never fails a successful
   run.

Before any generation, an **idempotency guard** checks the published index: if
today's date is already live, the run is skipped so a cron retry cannot
regenerate and replace an existing edition. Set `BOSCH_FORCE_REPUBLISH=1` to
intentionally rebuild a day.

The published edition goes live at
`https://kip.computer/apps/news-bosch/YYYY/MM/DD`.


## Publish

Publishing is automatic: the orchestrator runs `scripts/publish_to_site.py`
with `--publish` as a deterministic, token-free subprocess after the manifest
is built. It passes the exact date and the image model used, so no LLM
reasoning is involved in publishing. To run it manually (e.g. to re-publish a
previous run) invoke:

```bash
python scripts/publish_to_site.py \
  --run-dir "$RUN_DIR" \
  --repo "${HOME}/Code/kip-claw" \
  --date "<YYYY-MM-DD>" \
  --model "<provider/model from the image generation result>" \
  --publish
```

The command:

1. Converts the approved image to a web-optimized WebP.
2. Copies it to `static/images/news-bosch/YYYY/MM/DD.webp`.
3. Inserts or replaces that date in `src/lib/newsBosch.json`.
4. Records the exact image model and the `reuters-news-bosch` skill for the
   public AI disclosure.
5. Runs repo-local Prettier, `npm run lint`, `npm run check`, and
   `npm run build`.
6. With `--publish`, first asserts kip-claw is on a clean `main` (no other
   branch, no pre-existing staged changes) and aborts otherwise, then commits
   only the generated image and archive index, and pushes `main` with
   rebase-and-retry (`push_with_retry`) so a transient network error or a
   concurrent non-fast-forward push is retried with backoff.

Omit `--publish` to stage and validate a local preview without committing or
pushing.

## Files

Each run directory contains:

- `chartbeat.json`: immutable ranked source snapshot.
- `direction.json`: deterministic daily creative direction and recent motifs
  to avoid.
- `themes.json`: theme names, interpretations, and supporting story ranks.
- `themes-meta.json`: theme provenance (`themeSource`, model, motifs).
- `prompt.txt`: exact image prompt.
- `image-result.json`: raw image generation result envelope.
- `image.png`: generated artwork.
- `alt.txt`: visible composition description.
- `caption.md`: short disclosure and source-oriented caption.
- `manifest.json`: provenance and artifact metadata.
- `preview.md`: human-readable review sheet.

## Rules

- Every theme must cite at least one story rank from `chartbeat.json`.
- Use the date-seeded direction card so rerunning a date produces the same
  creative constraints.
- Record concrete motifs used in `manifest.json` after review. Future runs use
  recent manifests to discourage repetition.
- Keep factual story data separate from creative interpretation.
- Label the work as AI-generated editorial artwork based on a point-in-time
  Reuters Chartbeat ranking.
- Represent public figures symbolically unless identity is essential and
  supported by the reporting.
- Do not imply unsupported wrongdoing or private conduct.
- Do not substitute a homepage scrape if Chartbeat fails.
- Publishing is automatic and deterministic; it runs unattended with no model
  calls. If a run must be withheld, stop the orchestrator before the publish
  step rather than relying on a manual review gate.
- Treat replacing an existing date as an intentional revision and mention it
  in the commit message.
