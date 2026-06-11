#!/usr/bin/env python3
"""Resolve the generated image path from an image-generate result envelope.

Normalizes the produced file to <run-dir>/image.png and fails hard if the
output is missing or empty, so a failed generation never proceeds to delivery.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--result", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    run_dir = args.run_dir
    result_path = args.result or run_dir / "image-result.json"
    output_path = args.output or run_dir / "image.png"

    source = output_path
    if result_path.exists():
        try:
            data = json.loads(result_path.read_text(encoding="utf-8"))
            outputs = data.get("outputs") or []
            if outputs and isinstance(outputs[0], dict) and outputs[0].get("path"):
                source = Path(outputs[0]["path"])
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Could not parse {result_path}: {exc}", file=sys.stderr)

    if not source.exists() or source.stat().st_size == 0:
        print(
            f"Image generation failed: missing or empty image output ({source})",
            file=sys.stderr,
        )
        return 1

    if source.resolve() != output_path.resolve():
        shutil.copyfile(source, output_path)

    print(json.dumps({"image": str(output_path), "bytes": output_path.stat().st_size}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
