#!/usr/bin/env python3
"""Sanity-check a generated Bosch image before it is published.

With publishing now unattended, this replaces the old human review gate for the
mechanical failure modes: an unreadable file, the wrong shape (the fallback
lanes have produced 1:1 squares), a truncated/degenerate output, or a
near-blank frame. It performs no model calls and fails hard so a bad image is
never published.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from PIL import Image, ImageStat

# Both generation lanes must now return the Frame-ready native 4K canvas.
# Reject every other size rather than silently publishing an image that would
# require upscaling for the television.
EXPECTED_WIDTH = 3840
EXPECTED_HEIGHT = 2160
MIN_BYTES = 50_000
MIN_STDDEV = 8.0


def validate(image_path: Path) -> list[str]:
    problems: list[str] = []

    size_bytes = image_path.stat().st_size
    if size_bytes < MIN_BYTES:
        problems.append(f"file too small: {size_bytes} bytes < {MIN_BYTES}")

    try:
        with Image.open(image_path) as image:
            image.load()
            width, height = image.size
            grayscale = image.convert("L")
    except Exception as exc:  # noqa: BLE001 - any decode failure is a hard fail
        return [f"could not open image: {exc}"]

    if (width, height) != (EXPECTED_WIDTH, EXPECTED_HEIGHT):
        problems.append(
            "dimensions must be native 4K: "
            f"{width}x{height} != {EXPECTED_WIDTH}x{EXPECTED_HEIGHT}"
        )

    aspect = width / height if height else 0.0
    expected_aspect = EXPECTED_WIDTH / EXPECTED_HEIGHT
    if abs(aspect - expected_aspect) > 1e-9:
        problems.append(
            f"aspect ratio {aspect:.3f} is not 16:9 ({width}x{height})"
        )

    stddev = ImageStat.Stat(grayscale).stddev[0]
    if stddev < MIN_STDDEV:
        problems.append(
            f"image is near-blank: stddev {stddev:.2f} < {MIN_STDDEV}"
        )

    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--image", type=Path)
    args = parser.parse_args()

    if args.image:
        image_path = args.image
    elif args.run_dir:
        image_path = args.run_dir / "image.png"
    else:
        print("Provide --image or --run-dir", file=sys.stderr)
        return 2

    if not image_path.exists():
        print(f"Image not found: {image_path}", file=sys.stderr)
        return 1

    problems = validate(image_path)
    if problems:
        print(
            "Image failed validation: " + "; ".join(problems),
            file=sys.stderr,
        )
        return 1

    with Image.open(image_path) as image:
        width, height = image.size
    print(
        json.dumps(
            {
                "image": str(image_path),
                "bytes": image_path.stat().st_size,
                "width": width,
                "height": height,
                "aspect": round(width / height, 3) if height else 0.0,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
