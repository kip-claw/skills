#!/usr/bin/env python3
"""Upload and display one validated artwork, recording the exact Frame result."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, check=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frame-cli", required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--token-file", required=True)
    parser.add_argument("--matte", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--attempts", type=int, default=2)
    args = parser.parse_args()
    result: dict[str, object] = {"status": "failed", "host": args.host, "matte": args.matte}
    for attempt in range(1, args.attempts + 1):
        upload = run([args.frame_cli, "upload", str(args.image), "--host", args.host,
                      "--token-file", args.token_file, "--matte", args.matte, "--confirm-upload"])
        match = re.search(r"content_id:\s*([^\s]+)", upload.stdout)
        if upload.returncode == 0 and match:
            content_id = match.group(1)
            display = run([args.frame_cli, "display", content_id, "--host", args.host,
                           "--token-file", args.token_file, "--confirm-display"])
            if display.returncode == 0:
                result.update({"status": "displayed", "contentId": content_id, "attempt": attempt})
                args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
                print(json.dumps(result))
                return 0
            error = display.stderr.strip() or display.stdout.strip()
        else:
            error = upload.stderr.strip() or upload.stdout.strip() or "upload returned no content ID"
        result.update({"attempt": attempt, "error": error})
        if attempt < args.attempts:
            time.sleep(attempt * 5)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
