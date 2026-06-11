#!/usr/bin/env python3
"""Derive 3-6 editorial themes from a Chartbeat snapshot.

Primary path: ask the configured default OpenClaw model for themes as strict
JSON. Fallback path: a deterministic, content-aware rule-based deriver so the
edition always ships even when the model is throttled or unavailable.

themes.json is written as a LIST of {name, interpretation, storyRanks} so it
stays compatible with build_manifest.py and publish_to_site.py. Concrete
motifs and the theme source are reported on stdout for the orchestrator.
"""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import random
import re
import subprocess
import sys

MIN_THEMES = 3
MAX_THEMES = 6

# Deterministic fallback vocabulary. Section/keyword signals map to a theme
# label and an interpretation so the fallback still reflects the day's stories.
SECTION_THEMES = [
    (
        ("world", "politics", "us", "election", "government", "war", "ukraine", "gaza", "israel"),
        "Contested Power and Statecraft",
        "Governments, leaders, and institutions maneuver for advantage while the public absorbs the consequences.",
    ),
    (
        ("business", "markets", "finance", "economy", "tech", "deals", "money"),
        "Capital, Leverage, and Markets",
        "Firms and investors convert ownership, finance, and infrastructure into instruments of pressure and gain.",
    ),
    (
        ("legal", "crime", "court", "justice", "investigation"),
        "Law, Judgment, and Accountability",
        "Courts, investigators, and rules test who is held responsible and who escapes scrutiny.",
    ),
    (
        ("sports", "soccer", "olympics", "tennis", "football"),
        "Spectacle and Public Contest",
        "Public theater and competition amplify rivalry while masking unresolved stakes beneath the crowd.",
    ),
    (
        ("science", "health", "environment", "climate", "energy", "space"),
        "Nature, Risk, and Discovery",
        "Bodies, ecosystems, and frontiers strain under pressure as discovery and hazard advance together.",
    ),
    (
        ("entertainment", "lifestyle", "culture", "media", "arts"),
        "Culture, Attention, and Appetite",
        "Audiences chase novelty and meaning as culture and commerce compete for limited attention.",
    ),
]

GENERIC_THEMES = [
    (
        "Origins and Promises",
        "Institutions and actors set events in motion with pledges, plans, and unspoken costs.",
    ),
    (
        "Conflict Drawing the Crowd",
        "A central struggle pulls the most attention as competing interests collide in the open.",
    ),
    (
        "Consequences and Unresolved Futures",
        "Aftermath, risk, and warning accumulate while the outcome stays unsettled.",
    ),
]

MOTIF_NOUNS = [
    "grafted orchard",
    "spiral bridge",
    "tilted scales",
    "clockwork procession",
    "flooded market",
    "broken loom",
    "eclipsed tower",
    "masked assembly",
    "overturned vessel",
    "burning ledger",
    "migrating flock",
    "labyrinth stair",
]


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def build_prompt(stories: list[dict], direction: dict) -> str:
    story_lines = "\n".join(
        f"- rank {s['rank']}: {s['title']} "
        f"(sections: {', '.join(s.get('sections', []) or ['n/a'])}; "
        f"{s.get('readers', 0)} readers)"
        for s in stories
    )
    ranks = ", ".join(str(s["rank"]) for s in stories)
    return (
        "You are an editorial analyst. From the ranked Reuters most-read stories "
        "below, derive themes that capture the day's news for an allegorical "
        "illustration.\n\n"
        "Return ONLY a JSON array (no prose, no code fences) of "
        f"{MIN_THEMES} to {MAX_THEMES} objects. Each object must have:\n"
        '  "name": short title (3-6 words),\n'
        '  "interpretation": one sentence on what it means,\n'
        '  "storyRanks": array of integers, each an existing rank,\n'
        '  "motifs": array of 1-2 concrete, original visual nouns.\n\n'
        f"Valid ranks: {ranks}. Every storyRanks entry MUST be one of these. "
        "Each theme must cite at least one rank. Weight higher-ranked stories "
        "more, but treat reader counts only as a timestamped attention signal.\n\n"
        f"Creative direction for {direction.get('date', 'today')}: "
        f"symbol families {', '.join(direction.get('symbolFamilies', []))}; "
        f"narrative motion {direction.get('narrativeMotion', '')}.\n\n"
        "Ranked stories:\n"
        f"{story_lines}\n"
    )


def call_model(prompt: str, model: str | None, timeout: int) -> dict:
    command = [
        "openclaw",
        "infer",
        "model",
        "run",
        "--json",
        "--thinking",
        "off",
        "--prompt",
        prompt,
    ]
    if model:
        command[4:4] = ["--model", model]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=True,
    )
    return json.loads(result.stdout)


def extract_text(envelope: dict) -> str:
    outputs = envelope.get("outputs") or []
    if not outputs or not isinstance(outputs[0], dict):
        raise ValueError("model response has no outputs")
    text = outputs[0].get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("model response has empty text")
    return text


def parse_themes_text(text: str) -> list[dict]:
    cleaned = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1).strip()
    data = json.loads(cleaned)
    if not isinstance(data, list):
        raise ValueError("themes payload is not a list")
    return data


def validate_themes(themes: list[dict], valid_ranks: set[int]) -> tuple[list[dict], list[str]]:
    if not MIN_THEMES <= len(themes) <= MAX_THEMES:
        raise ValueError(f"expected {MIN_THEMES}-{MAX_THEMES} themes, got {len(themes)}")
    normalized: list[dict] = []
    motifs: list[str] = []
    for theme in themes:
        if not isinstance(theme, dict):
            raise ValueError("theme is not an object")
        name = str(theme.get("name", "")).strip()
        interpretation = str(theme.get("interpretation", "")).strip()
        if not name or not interpretation:
            raise ValueError("theme missing name or interpretation")
        raw_ranks = theme.get("storyRanks") or []
        if not isinstance(raw_ranks, list) or not raw_ranks:
            raise ValueError(f"theme '{name}' has no storyRanks")
        ranks: list[int] = []
        for value in raw_ranks:
            rank = int(value)
            if rank not in valid_ranks:
                raise ValueError(f"theme '{name}' cites unknown rank {rank}")
            ranks.append(rank)
        normalized.append(
            {"name": name, "interpretation": interpretation, "storyRanks": ranks}
        )
        for motif in theme.get("motifs") or []:
            motif = str(motif).strip()
            if motif:
                motifs.append(motif)
    return normalized, list(dict.fromkeys(motifs))


def fallback_themes(
    stories: list[dict], run_date: str
) -> tuple[list[dict], list[str]]:
    seed = int(hashlib.sha256(run_date.encode("ascii")).hexdigest()[:16], 16)
    rng = random.Random(seed)

    matched: dict[str, dict] = {}
    for story in stories:
        haystack = " ".join(
            [story.get("title", "")] + list(story.get("sections", []) or [])
        ).lower()
        for keywords, name, interpretation in SECTION_THEMES:
            if any(word in haystack for word in keywords):
                bucket = matched.setdefault(
                    name,
                    {"name": name, "interpretation": interpretation, "storyRanks": []},
                )
                bucket["storyRanks"].append(story["rank"])
                break

    themes = [t for t in matched.values() if t["storyRanks"]]
    themes.sort(key=lambda t: min(t["storyRanks"]))

    # Top up with generic themes anchored to the highest-ranked stories.
    top_ranks = [s["rank"] for s in stories[:5]]
    generic_iter = iter(GENERIC_THEMES)
    while len(themes) < MIN_THEMES:
        name, interpretation = next(generic_iter)
        if any(t["name"] == name for t in themes):
            continue
        anchor = top_ranks[len(themes) % len(top_ranks)]
        themes.append(
            {"name": name, "interpretation": interpretation, "storyRanks": [anchor]}
        )

    themes = themes[:MAX_THEMES]
    motifs = rng.sample(MOTIF_NOUNS, k=min(3, len(MOTIF_NOUNS)))
    return themes, motifs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chartbeat", type=Path, required=True)
    parser.add_argument("--direction", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--model",
        default=None,
        help="Optional provider/model override; defaults to the configured model.",
    )
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument(
        "--force-fallback",
        action="store_true",
        help="Skip the model call and use the deterministic deriver (for testing).",
    )
    args = parser.parse_args()

    snapshot = read_json(args.chartbeat)
    direction = read_json(args.direction)
    stories = snapshot.get("stories", [])
    if len(stories) < 5:
        print("Need at least five stories in the snapshot", file=sys.stderr)
        return 1
    valid_ranks = {story["rank"] for story in stories}
    run_date = direction.get("date") or snapshot.get("retrievedAt", "")[:10] or date.today().isoformat()

    theme_source = "fallback"
    used_model = None
    used_provider = None
    themes: list[dict] = []
    motifs: list[str] = []

    if not args.force_fallback:
        try:
            prompt = build_prompt(stories, direction)
            envelope = call_model(prompt, args.model, args.timeout)
            text = extract_text(envelope)
            parsed = parse_themes_text(text)
            themes, motifs = validate_themes(parsed, valid_ranks)
            theme_source = "model"
            used_model = envelope.get("model")
            used_provider = envelope.get("provider")
        except (
            subprocess.SubprocessError,
            json.JSONDecodeError,
            ValueError,
            OSError,
        ) as exc:
            print(f"Theme model call failed, using fallback: {exc}", file=sys.stderr)
            themes = []

    if not themes:
        theme_source = "fallback"
        themes, motifs = fallback_themes(stories, run_date)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(themes, ensure_ascii=True, indent=2) + "\n", encoding="utf-8"
    )
    meta = {
        "themeSource": theme_source,
        "model": used_model,
        "provider": used_provider,
        "themeCount": len(themes),
        "motifs": motifs,
    }
    (args.output.parent / "themes-meta.json").write_text(
        json.dumps(meta, ensure_ascii=True, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"output": str(args.output), **meta}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
