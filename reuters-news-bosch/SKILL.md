---
name: "reuters-news-bosch"
description: "Generate sourced Bosch-inspired editorial images from Reuters Chartbeat most-read stories."
---

# Reuters News Bosch

Generate a review-only daily news allegory from Reuters Chartbeat's most-read
stories. Use `scripts/chartbeat_snapshot.py` for source capture and the
OpenClaw image generation tool for the image.

## Generate

1. Create a dated run directory:

   ```bash
   RUN_DIR="${HOME}/.openclaw/workspace/tmp/reuters-news-bosch/$(date +%F-%H%M%S)"
   mkdir -p "$RUN_DIR"
   python scripts/chartbeat_snapshot.py --limit 10 --output "$RUN_DIR/chartbeat.json"
   python scripts/direction_card.py \
     --date "$(date +%F)" \
     --runs-root "${HOME}/.openclaw/workspace/tmp/reuters-news-bosch" \
     --output "$RUN_DIR/direction.json"
   ```

2. Read `chartbeat.json` and `direction.json`. Stop if the snapshot contains
   fewer than five stories.
3. Derive 3-6 themes. Weight high-ranked stories and reader counts, but treat
   counts only as a timestamped attention signal. Write them to `themes.json`
   using the `file_write` tool (never a shell heredoc such as `cat <<EOF`,
   which forces a manual approval prompt).
4. Build a panoramic three-part allegory using every field in the creative
   direction card:
   - Left: origins, causes, institutions, or promises.
   - Center: the activity and conflict drawing the most attention.
   - Right: aftermath, risks, warnings, or unresolved futures.
   - Prefer the selected symbol families and character archetypes.
   - Follow the selected composition, atmosphere, palette, scale, and
     narrative motion.
   - Avoid every item in `avoidRecentMotifs` unless today's reporting makes it
     uniquely necessary. If reused, explain why in `themes.json`.
5. Write the exact assembled prompt to `prompt.txt` with the `file_write` tool
   (never a shell heredoc). Include this instruction:
   "Invent a fresh symbolic vocabulary for this edition. Do not default to
   familiar editorial symbols when the direction card offers a less literal
   metaphor."
6. Generate one `16:9` landscape image with the OpenClaw image tool. Call
   `image_generate` **without a `model` argument** so it uses the configured
   default image model (never pass a bare `google/...` ref). Use an
   intricate Northern Renaissance oil-painting aesthetic inspired by
   Hieronymus Bosch and triptych composition, while creating original symbols
   and scenes. No copied artwork, Reuters marks, logos, embedded text,
   photorealistic news imagery, or graphic gore.
7. Save the final image as `image.png` in the run directory.
8. Create the remaining artifacts with:

   ```bash
   python scripts/build_manifest.py \
     --run-dir "$RUN_DIR" \
     --prompt-file "$RUN_DIR/prompt.txt" \
     --themes-file "$RUN_DIR/themes.json" \
     --direction-file "$RUN_DIR/direction.json" \
     --alt-file "$RUN_DIR/alt.txt" \
     --caption-file "$RUN_DIR/caption.md"
   ```

9. Inspect `image.png`. Verify it is a wide triptych, contains no legible text
   or logos, avoids documentary realism and graphic injury, and visibly
   represents each declared theme and the direction card. Compare it with the
   most recent image when available. Regenerate once with a targeted correction
   if the visual vocabulary is too similar.
10. Present the image and `preview.md` for review.

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
- `prompt.txt`: exact image prompt.
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
