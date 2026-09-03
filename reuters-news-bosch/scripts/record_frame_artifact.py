#!/usr/bin/env python3
"""Attach the private Frame stage's recorded result to a Bosch manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--status", required=True)
    args = parser.parse_args()
    manifest_path = args.run_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    frame = {"status": args.status}
    for filename, key in (("frame-vellum.json", "vellum"), ("frame-art.json", "display")):
        path = args.run_dir / filename
        if path.exists():
            frame[key] = json.loads(path.read_text(encoding="utf-8"))
    manifest["frameArt"] = frame
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
