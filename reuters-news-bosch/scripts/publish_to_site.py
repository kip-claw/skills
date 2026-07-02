#!/usr/bin/env python3
"""Publish an approved Reuters News Bosch run to the kip-claw site."""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import subprocess
import sys
import time

from PIL import Image


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def run(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def assert_publish_preconditions(repo: Path) -> None:
    """Refuse to publish unless kip-claw is on a clean ``main``.

    Guards unattended auto-publish: if the checkout is on another branch or
    already has staged changes, abort before mutating anything so a publish
    commit never sweeps in unrelated work. Raises ``ValueError`` on violation,
    which the top-level handler turns into a clean non-zero exit.
    """
    branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if branch != "main":
        raise ValueError(f"repo is on branch '{branch}', expected 'main'")
    if subprocess.run(
        ["git", "diff", "--cached", "--quiet"], cwd=repo, check=False
    ).returncode:
        raise ValueError("repo has staged changes; refusing to publish")


def push_with_retry(repo: Path, attempts: int = 4) -> None:
    """Rebase onto origin/main and push, retrying transient failures.

    A concurrent push produces a non-fast-forward; re-pulling with rebase and
    pushing again resolves it. Network blips are retried with linear backoff.
    The commit is already made locally, so a failed attempt is safe to retry.
    """
    last_error: subprocess.CalledProcessError | None = None
    for attempt in range(1, attempts + 1):
        try:
            run(["git", "pull", "--rebase", "--autostash", "origin", "main"], repo)
            run(["git", "push", "origin", "main"], repo)
            return
        except subprocess.CalledProcessError as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(attempt * 5)
    assert last_error is not None
    raise last_error


def display_date(value: str) -> str:
    parsed = date.fromisoformat(value)
    return parsed.strftime("%B %-d, %Y")


def build_entry(
    run_dir: Path, image_url: str, run_date: str, image_model: str
) -> dict:
    source = read_json(run_dir / "chartbeat.json")
    themes = read_json(run_dir / "themes.json")
    manifest = read_json(run_dir / "manifest.json")
    direction = manifest.get("creativeDirection")
    if not direction:
        direction_path = run_dir / "direction.json"
        if direction_path.exists():
            direction = read_json(direction_path)
    if not direction:
        raise ValueError("Run is missing creative direction metadata")

    stories = [
        {
            "title": story["title"],
            "url": story["url"],
        }
        for story in source["stories"]
    ]
    shown_date = display_date(run_date)
    skill_name = "reuters-news-bosch"
    return {
        "date": run_date,
        "displayDate": shown_date,
        "image": image_url,
        "alt": (run_dir / "alt.txt").read_text(encoding="utf-8").strip(),
        "disclosure": (
            f"Generated with AI using {image_model} and the {skill_name} skill."
        ),
        "aiModel": image_model,
        "skill": skill_name,
        "generatedAt": manifest["generatedAt"],
        "sourceRetrievedAt": source["retrievedAt"],
        "themes": themes,
        "stories": stories,
        "creativeDirection": {
            key: direction[key]
            for key in (
                "characters",
                "symbolFamilies",
                "composition",
                "atmosphere",
                "palette",
                "scale",
                "narrativeMotion",
            )
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--date")
    parser.add_argument("--model")
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    repo = args.repo.resolve()
    image_path = run_dir / "image.png"
    index_path = repo / "src/lib/newsBosch.json"
    prettier = repo / "node_modules/.bin/prettier"

    required = [
        image_path,
        run_dir / "chartbeat.json",
        run_dir / "themes.json",
        run_dir / "manifest.json",
        run_dir / "alt.txt",
        run_dir / "caption.md",
        index_path,
        prettier,
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        print("Missing required files: " + ", ".join(missing), file=sys.stderr)
        return 1

    if args.publish:
        assert_publish_preconditions(repo)

    source = read_json(run_dir / "chartbeat.json")
    run_date = args.date or source["retrievedAt"][:10]
    date.fromisoformat(run_date)
    year, month, day = run_date.split("-")
    relative_image = Path("static/images/news-bosch") / year / month / f"{day}.webp"
    destination = repo / relative_image
    destination.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(image_path) as image:
        image = image.convert("RGB")
        image.thumbnail((1800, 1800), Image.Resampling.LANCZOS)
        image.save(destination, "WEBP", quality=88, method=6)

    manifest = read_json(run_dir / "manifest.json")
    image_model = (
        args.model
        or manifest.get("imageModel")
        or manifest.get("imageProvider")
        or "unknown image model"
    )
    entry = build_entry(
        run_dir,
        "/" + str(relative_image.relative_to("static")),
        run_date,
        image_model,
    )
    entries = read_json(index_path)
    entries = [existing for existing in entries if existing.get("date") != run_date]
    entries.append(entry)
    entries.sort(key=lambda item: item["date"], reverse=True)
    index_path.write_text(
        json.dumps(entries, ensure_ascii=True, indent=2) + "\n", encoding="utf-8"
    )

    run([str(prettier), "--write", "src/lib/newsBosch.json"], repo)
    run(["npm", "run", "lint"], repo)
    run(["npm", "run", "check"], repo)
    run(["npm", "run", "build"], repo)

    if args.publish:
        run(["git", "add", "-f", str(relative_image)], repo)
        run(["git", "add", "src/lib/newsBosch.json"], repo)
        staged = subprocess.run(
            ["git", "diff", "--cached", "--quiet"], cwd=repo, check=False
        )
        if staged.returncode:
            run(
                [
                    "git",
                    "commit",
                    "--no-verify",
                    "-m",
                    f"Publish Daily Bosch edition for {run_date}",
                ],
                repo,
            )
            push_with_retry(repo)

    print(
        json.dumps(
            {
                "date": run_date,
                "image": str(destination),
                "index": str(index_path),
                "published": args.publish,
            }
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"Publish failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
