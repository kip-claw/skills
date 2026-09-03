---
name: "reuters-news-bosch"
description: "Add a post-publish, image-to-image vellum Frame stage using Samsung's flexible antique matte."
tag: Work
---

# Reuters News Bosch

Generate a daily news allegory from Reuters Chartbeat's most-read stories, publish the full-color edition to kip.computer, and then automatically create and display a monochrome vellum interpretation on Ben's Samsung Frame. The public color edition and the private Frame edition are separate artifacts. The entire pipeline is deterministic apart from the two explicitly recorded image-generation calls.

## Generate

Run the allowlisted orchestrator:

```bash
{{HOME}}/bin/reuters-news-bosch-cron.sh
```

It writes each run to `{{HOME}}/.openclaw/workspace/tmp/reuters-news-bosch/<timestamp>/`:

1. Create an immutable Chartbeat snapshot, date-seeded direction card, sourced themes, and the color-edition prompt/alt/caption.
2. Generate the public color artwork with `gpt-image-2` at exactly 3840×2160 PNG through the primary OpenClaw route, retaining the existing direct OpenAI API fallback, retries, provenance, and 4K validator.
3. Build the manifest and publish the color edition to `https://kip.computer/apps/news-bosch/YYYY/MM/DD`. This remains a hard requirement: if it fails, do not attempt the Frame stage.
4. After a successful public publish, create a private Frame rendition from the validated `image.png` using the OpenAI Images **edits** endpoint and the same `gpt-image-2` model. Submit the color image as the edit input; do not recreate the scene from text alone. Request a 3840×2160 PNG with this purpose-built transformation prompt:

   ```
   Transform this exact Daily Bosch artwork into a restrained monochrome vellum illustration for a Samsung Frame display. Preserve the complete composition, all meaningful figures, objects, and spatial relationships from the supplied image. Render it in warm parchment, sepia, charcoal, and muted ivory tones: antique paper texture, fine engraved or ink-wash linework, subtle hand-tinted shading, no vivid color, no caption, no signature, no new border, and no simulated physical frame. Keep an exact 16:9 landscape composition at 3840×2160.
   ```

   Save the result as `frame-vellum.png`; write the edit response to `frame-vellum-result.json`; add the prompt, model, requested size, source SHA-256, output SHA-256, output dimensions, and status to `frame-vellum.json` and the main manifest.
5. Validate `frame-vellum.png` with the existing image validator, requiring a readable, nonblank, exact native 3840×2160 16:9 PNG. Never crop, center-crop, pad, resize, or bake a matte into either artifact.
6. Use the locally installed Frame client directly from its source environment, with the already paired TV and token:
   ```bash
   {{HOME}}/Code/art.kip.computer/.venv/bin/frame-art upload <frame-vellum.png> --host 192.168.0.110 --token-file {{HOME}}/.openclaw/frame-art-token --matte flexible_antique --confirm-upload
   {{HOME}}/Code/art.kip.computer/.venv/bin/frame-art display <returned-content-id> --host 192.168.0.110 --token-file {{HOME}}/.openclaw/frame-art-token --confirm-display
   ```
   If the `frame-art` console script is unavailable, invoke the same installed project with its documented Python module and explicit `PYTHONPATH={{HOME}}/Code/art.kip.computer/src`; do not rely on a workspace-relative command. Record the content ID, matte (`flexible_antique`), host, and display result in `frame-art.json` and the manifest.
7. Send the usual Telegram notification after the publish and Frame attempt. Include the public URL and one concise Frame status: displayed (with content ID), or published but Frame skipped/failed. Retain the color image as the Telegram media.

## Implementation requirements

Update `{{HOME}}/bin/reuters-news-bosch-cron.sh` and add small testable helpers under `skills/reuters-news-bosch/scripts/` as needed.

- Preserve `IMAGE_PRIMARY_SIZE=3840x2160`, `IMAGE_DIRECT_SIZE=3840x2160`, current primary/fallback behavior, idempotency guard, publishing flow, and color provenance.
- Implement the image-to-image vellum operation with the OpenAI Images edits API and multipart upload; do not use a text-only generation call, and do not place API keys in run artifacts, logs, command arguments, manifests, or Telegram.
- The Frame stage starts only after site publication succeeds. Its failure is non-fatal to the already-live public edition: log and notify the failure, preserve all artifacts, and exit successfully with a clear `published; frame ... failed` status. A color-generation or public-publish failure remains fatal as today.
- Add bounded retries for the vellum edit and the Frame upload/display. Do not retry a completed site publish. On retry, use the same `frame-vellum.png` if generation already validated; do not create an untracked alternate.
- Add tests using mocked HTTP and Frame client calls that verify: edit request includes the color source image and 3840×2160 request; vellum prompt is captured; non-4K vellum output is rejected; upload uses `flexible_antique`; display follows a successful upload; Frame failure does not change a successful publication outcome; no TV action happens when public publication fails.
- Keep the daily run idempotent. A normal rerun after a fully published day skips as before; `BOSCH_FORCE_REPUBLISH=1` is the only permitted way to deliberately replace the date.

## Rules

- Every theme must cite the immutable Chartbeat snapshot.
- Keep source facts separate from interpretation and label the public artwork AI-generated.
- The public color artwork must remain untouched for publishing; the Frame vellum is a separate, private derivative.
- Never bake in a physical matte or border. Samsung applies `flexible_antique` at display time so the composition is not crop-to-fill.
- Do not let a Frame or Telegram failure turn an already published edition into a failed publication.
