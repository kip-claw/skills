#!/usr/bin/env python3
"""Generate Reuters audiobook files from Chartbeat top stories.

This helper is designed for unattended cron use and always prints a final JSON
manifest on success:
  {"files": [...], "stories": [...]}.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib import parse, request

HOME = Path("{{HOME}}")
WORKSPACE = Path("{{HOME}}/.openclaw/workspace")
ENV_FILE = HOME / ".openclaw/.env"
AUDIOBOOK_WRAPPER = HOME / "bin/article-audiobook-render.sh"
CHARTBEAT_HOST = "reuters.com"
CHARTBEAT_LIMIT_DEFAULT = 5


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _normalize_reuters_url(path_or_url: str, host: str) -> str:
    val = (path_or_url or "").strip()
    if not val:
        return f"https://{host}/"
    if val.startswith("http://") or val.startswith("https://"):
        return val
    if val.startswith("//"):
        return f"https:{val}"
    if val.startswith(host + "/"):
        return f"https://{val}"
    if val.startswith("/"):
        return f"https://{host}{val}"
    return f"https://{host}/{val}"


def _slugify(text: str) -> str:
    keep = []
    for ch in text.lower():
        if ch.isalnum():
            keep.append(ch)
        elif ch in {" ", "-", "_"}:
            keep.append("-")
    slug = "".join(keep)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "story"


def _fetch_chartbeat_pages(limit: int, host: str, api_key: str) -> list[dict[str, Any]]:
    fetch_limit = limit + 5
    query = parse.urlencode(
        {
            "apikey": api_key,
            "host": host,
            "limit": str(fetch_limit),
        }
    )
    url = f"https://api.chartbeat.com/live/toppages/v3/?{query}"
    with request.urlopen(url, timeout=45) as resp:  # noqa: S310
        body = resp.read().decode("utf-8")
    data = json.loads(body)
    pages = data.get("pages", [])
    story_pages = [p for p in pages if p.get("stats", {}).get("article", 0) > 0]
    return story_pages[:limit]


def _extract_json_from_stdout(stdout: str) -> dict[str, Any]:
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    for line in reversed(lines):
        if not line.startswith("{"):
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    raise ValueError("No JSON object found in audiobook output")


def _run_audiobook(url: str, title: str, env: dict[str, str]) -> dict[str, Any]:
    cmd = [str(AUDIOBOOK_WRAPPER), url]
    proc = subprocess.run(
        cmd,
        cwd=str(WORKSPACE),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return {
            "failed": True,
            "error": (proc.stderr or proc.stdout or "audiobook command failed").strip(),
            "path": None,
            "duration_seconds": None,
            "runtime": None,
        }
    try:
        payload = _extract_json_from_stdout(proc.stdout)
    except Exception as exc:  # noqa: BLE001
        return {
            "failed": True,
            "error": f"audiobook output parse failure: {exc}",
            "path": None,
            "duration_seconds": None,
            "runtime": None,
        }

    file_path = payload.get("file") or payload.get("output") or payload.get("path")
    if not file_path:
        date_prefix = payload.get("date") or ""
        maybe_slug = _slugify(title)
        guessed = HOME / "audiobooks" / f"{date_prefix}_{maybe_slug}.mp3"
        file_path = str(guessed)

    if not Path(file_path).exists():
        return {
            "failed": True,
            "error": f"audiobook output file missing: {file_path}",
            "path": file_path,
            "duration_seconds": payload.get("duration_seconds"),
            "runtime": payload.get("runtime"),
        }

    return {
        "failed": False,
        "error": None,
        "path": file_path,
        "duration_seconds": payload.get("duration_seconds"),
        "runtime": payload.get("runtime") or payload.get("duration"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Reuters Chartbeat audiobooks")
    parser.add_argument("--limit", type=int, default=CHARTBEAT_LIMIT_DEFAULT)
    parser.add_argument("--host", default=CHARTBEAT_HOST)
    args = parser.parse_args()

    if args.limit < 1:
        print("--limit must be >= 1", file=sys.stderr)
        return 2

    _load_env_file(ENV_FILE)

    api_key = os.environ.get("CHARTBEAT_API_KEY")
    if not api_key:
        print("CHARTBEAT_API_KEY is missing", file=sys.stderr)
        return 2
    if not AUDIOBOOK_WRAPPER.exists():
        print(f"Missing wrapper: {AUDIOBOOK_WRAPPER}", file=sys.stderr)
        return 2

    try:
        pages = _fetch_chartbeat_pages(args.limit, args.host, api_key)
    except Exception as exc:  # noqa: BLE001
        print(f"Chartbeat fetch failed: {exc}", file=sys.stderr)
        return 1

    if not pages:
        print("No story pages returned from Chartbeat", file=sys.stderr)
        return 1

    env = os.environ.copy()
    stories: list[dict[str, Any]] = []
    files: list[str] = []

    for idx, page in enumerate(pages, start=1):
        title = page.get("title") or "(no title)"
        readers = int(page.get("stats", {}).get("people", 0) or 0)
        url = _normalize_reuters_url(page.get("path", ""), args.host)

        print(f"[{idx}/{len(pages)}] Rendering: {title}")
        result = _run_audiobook(url, title, env)

        story = {
            "rank": idx,
            "title": title,
            "url": url,
            "people": readers,
            "runtime": result.get("runtime"),
            "duration_seconds": result.get("duration_seconds"),
            "path": result.get("path"),
            "failed": result.get("failed", True),
            "error": result.get("error"),
        }
        stories.append(story)
        if not story["failed"] and story["path"]:
            files.append(str(story["path"]))

    manifest = {"files": files, "stories": stories}
    print(json.dumps(manifest, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
