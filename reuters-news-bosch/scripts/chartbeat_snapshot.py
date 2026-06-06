#!/usr/bin/env python3
"""Capture a timestamped Reuters Chartbeat top-story snapshot."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from typing import Any
from urllib import parse, request

DEFAULT_ENV = Path.home() / ".openclaw/.env"
DEFAULT_HOST = "reuters.com"


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def normalize_url(value: str, host: str) -> str:
    value = value.strip()
    if value.startswith(("http://", "https://")):
        return value
    if value.startswith("//"):
        return f"https:{value}"
    if value.startswith(f"{host}/"):
        return f"https://{value}"
    if value.startswith("/"):
        return f"https://{host}{value}"
    return f"https://{host}/{value.lstrip('/')}"


def fetch_pages(api_key: str, host: str, limit: int) -> list[dict[str, Any]]:
    query = parse.urlencode(
        {"apikey": api_key, "host": host, "limit": max(limit + 10, 20)}
    )
    url = f"https://api.chartbeat.com/live/toppages/v3/?{query}"
    req = request.Request(url, headers={"User-Agent": "reuters-news-bosch/1.0"})
    with request.urlopen(req, timeout=45) as response:  # noqa: S310
        payload = json.load(response)
    pages = payload.get("pages", [])
    stories = [page for page in pages if page.get("stats", {}).get("article", 0) > 0]
    return stories[:limit]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    args = parser.parse_args()

    if args.limit < 5:
        parser.error("--limit must be at least 5")

    load_env(args.env_file)
    api_key = os.environ.get("CHARTBEAT_API_KEY")
    if not api_key:
        print("CHARTBEAT_API_KEY is missing", file=sys.stderr)
        return 2

    try:
        pages = fetch_pages(api_key, args.host, args.limit)
    except Exception as exc:  # noqa: BLE001
        print(f"Chartbeat fetch failed: {exc}", file=sys.stderr)
        return 1

    if len(pages) < 5:
        print(f"Chartbeat returned only {len(pages)} suitable stories", file=sys.stderr)
        return 1

    retrieved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    stories = []
    for rank, page in enumerate(pages, start=1):
        stories.append(
            {
                "rank": rank,
                "readers": int(page.get("stats", {}).get("people", 0) or 0),
                "title": page.get("title") or "(untitled)",
                "url": normalize_url(page.get("path", ""), args.host),
                "authors": page.get("authors", []),
                "sections": page.get("sections", []),
            }
        )

    output = {
        "schemaVersion": 1,
        "source": "Chartbeat live toppages v3",
        "host": args.host,
        "retrievedAt": retrieved_at,
        "metric": "concurrent readers",
        "stories": stories,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=True, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"output": str(args.output), "stories": len(stories)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
