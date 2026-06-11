---
name: "reuters-news-bosch"
description: "Generate sourced Bosch-inspired editorial images from Reuters Chartbeat most-read stories."
---

# Reuters News Bosch

Generate a review-only daily news allegory from Reuters Chartbeat's most-read
stories. The pipeline is deterministic and runs unattended from a single
orchestrator script; only publishing to the public site requires human review.

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
6. `scripts/build_manifest.py --meta-file themes-meta.json` — writes
   `manifest.json` (provenance, `themeSource`, `motifsUsed`) and `preview.md`.
   Recording `motifsUsed` re-enables motif repetition control for future runs.
7. Telegram delivery — sends the image preview for review. On any failure the
   orchestrator sends a concise Telegram failure notice and logs to
   `${HOME}/.openclaw/logs/kip-reuters-news-bosch.log`.

To review, open the image and `preview.md` in the run directory. Verify it is a
wide triptych, contains no legible text or logos, avoids documentary realism and
graphic injury, and visibly represents each declared theme and the direction
card. Publishing is a separate, explicit step (below).


## Publish

Only publish after the user approves the reviewed image. Run:

```bash
python scripts/publish_to_site.py \
  --run-dir "$RUN_DIR" \
  --repo "${HOME}/Code/kip-claw" \
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
6. With `--publish`, commits only the generated image and archive index, pulls
   with rebase, and pushes `main`.

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
- Never publish an unreviewed image.
- Treat replacing an existing date as an intentional revision and mention it
  in the commit message.
