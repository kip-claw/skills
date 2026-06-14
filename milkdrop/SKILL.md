---
name: milkdrop
description: Render a MilkDrop/Butterchurn audio visualization video from an audio/video file or a YouTube/audio URL, then send the MP4 back to the user. Use when someone shares audio or a link and asks for a visualizer, music video, milkdrop, or trippy visualization.
metadata: {"openclaw": {"emoji": "🌀", "requires": {"bins": ["node", "ffmpeg", "ffprobe", "yt-dlp"]}}}
---

# MilkDrop Visualizer

Turn audio into a MilkDrop/Butterchurn visualization MP4 and deliver it back to
the requester. Triggered when a user sends an audio/video file or a link
(YouTube or a direct audio URL) and asks for a visualizer / music video /
"milkdrop" / trippy visuals.

## Run

Everything runs from one allowlisted wrapper:

```bash
{{HOME}}/bin/milkdrop-render.sh --input <url-or-file> [options]
```

Options:

- `--input` YouTube/audio URL **or** a local audio/video file path (required)
- `--output` MP4 path (optional; defaults to
  `~/.openclaw/media/outbound/milkdrop-<timestamp>.mp4`)
- `--duration` clip length in seconds (default 30)
- `--start` start offset in seconds (default 0)
- `--width` / `--height` canvas size
- `--fps` frames per second (default 30)
- `--preset` preset name, index, or `random` (default random)

Aspect shortcuts (pass the matching `--width`/`--height`):

- vertical / story / reel — `--width 1080 --height 1920` (default)
- square — `--width 1080 --height 1080`
- landscape — `--width 1920 --height 1080`

On success the script prints a single-line JSON summary to stdout, e.g.

```json
{"ok":true,"path":"{{HOME}}/.openclaw/media/outbound/milkdrop-20260612-143012.mp4","preset":"...","duration":30,"width":1080,"height":1920}
```

## Workflow

1. **Resolve the input.**
   - If the user pasted a URL, pass it directly with `--input <url>`.
   - If the user sent an audio/video file, use the inbound media path
     (`~/.openclaw/media/inbound/...`) as `--input`.
2. **Pick options from the request.** Honor any requested length (`--duration`)
   and aspect ratio (defaults to vertical). Keep `--duration` modest (≤ 60s)
   unless the user explicitly asks for longer — rendering is real-time plus a
   transcode pass.
3. **Run** `{{HOME}}/bin/milkdrop-render.sh` with the chosen options.
4. **Parse** the JSON summary line and read `path`.
5. **Deliver** the MP4 back on the same channel the request came in on:

   ```bash
   openclaw message send --channel <channel> --target <chat-id> \
     --media "<path>" --force-document \
     -m "Here's your MilkDrop visualization 🌀 (preset: <preset>)"
   ```

   Use `--force-document` so the video is not re-compressed by the channel.

## Notes

- Remote URLs require `yt-dlp` (at `/usr/local/bin/yt-dlp`); local files only
  need `ffmpeg`/`ffprobe`.
- Output files accumulate in `~/.openclaw/media/outbound/`; old renders are safe
  to clean up.
- On failure the script exits non-zero and writes the error to stderr. Reply
  with a short, friendly note and the gist of the error.
