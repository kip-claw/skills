#!/usr/bin/env python3
"""Create a private, image-to-image vellum edition for Samsung The Frame."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from PIL import Image

PROMPT = (
    "Transform this exact Daily Bosch artwork into a restrained monochrome vellum "
    "illustration for a Samsung Frame display. Preserve the complete composition, "
    "all meaningful figures, objects, and spatial relationships from the supplied "
    "image. Render it in warm parchment, sepia, charcoal, and muted ivory tones: "
    "antique paper texture, fine engraved or ink-wash linework, subtle hand-tinted "
    "shading, no vivid color, no caption, no signature, no new border, and no "
    "simulated physical frame. Keep an exact 16:9 landscape composition at 3840×2160."
)


def _part(boundary: str, name: str, value: bytes, *, filename: str | None = None,
          content_type: str | None = None) -> bytes:
    headers = [f"--{boundary}", f'Content-Disposition: form-data; name="{name}"']
    if filename:
        headers[-1] += f'; filename="{filename}"'
    if content_type:
        headers.append(f"Content-Type: {content_type}")
    return ("\r\n".join(headers).encode() + b"\r\n\r\n" + value + b"\r\n")


def request_edit(source: Path, api_key: str) -> tuple[bytes, dict[str, object]]:
    boundary = f"----kip-vellum-{uuid.uuid4().hex}"
    body = b"".join(
        [
            _part(boundary, "model", b"gpt-image-2"),
            _part(boundary, "prompt", PROMPT.encode()),
            _part(boundary, "size", b"3840x2160"),
            _part(boundary, "n", b"1"),
            _part(boundary, "output_format", b"png"),
            _part(boundary, "image", source.read_bytes(), filename=source.name,
                  content_type="image/png"),
            f"--{boundary}--\r\n".encode(),
        ]
    )
    request = Request(
        "https://api.openai.com/v1/images/edits",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    try:
        with urlopen(request, timeout=600) as response:
            payload = json.load(response)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        if exc.code == 429:
            raise RuntimeError(
                "OpenAI vellum edit request failed: HTTP 429. This may indicate "
                "exhausted API credits, billing/quota limits, or a temporary rate limit. "
                f"Provider response: {detail}"
            ) from exc
        raise RuntimeError(f"OpenAI vellum edit request failed: HTTP {exc.code}: {detail}") from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError(f"OpenAI vellum edit request failed: {exc}") from exc
    encoded = (payload.get("data") or [{}])[0].get("b64_json")
    if not encoded:
        raise RuntimeError("OpenAI vellum edit returned no image data")
    return base64.b64decode(encoded), payload


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--response", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    args = parser.parse_args()
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is required for the vellum edit")
    if not args.source.is_file():
        raise SystemExit(f"Missing color source image: {args.source}")
    image_bytes, response = request_edit(args.source, api_key)
    args.output.write_bytes(image_bytes)
    with Image.open(args.output) as image:
        dimensions = [image.width, image.height]
    # Retain response provenance without storing a second base64 copy of the image.
    safe_response = {key: value for key, value in response.items() if key != "data"}
    safe_response["data"] = [{"image": "frame-vellum.png"}]
    args.response.write_text(json.dumps(safe_response, indent=2) + "\n", encoding="utf-8")
    metadata = {
        "status": "generated",
        "model": "gpt-image-2",
        "endpoint": "/v1/images/edits",
        "requestedSize": "3840x2160",
        "prompt": PROMPT,
        "source": args.source.name,
        "sourceSha256": sha256(args.source),
        "output": args.output.name,
        "outputSha256": sha256(args.output),
        "dimensions": dimensions,
    }
    args.metadata.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metadata))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"frame vellum generation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
