#!/usr/bin/env python3
"""Assemble the image prompt, alt text, and caption for a Bosch edition.

Deterministic: given the same snapshot, direction card, and themes, it always
produces the same prompt.txt, alt.txt, and caption.md. This replaces the inline
heredoc logic that previously lived in the cron runner.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

DISCLOSURE = (
    "AI-generated editorial artwork based on a point-in-time Reuters Chartbeat "
    "ranking of concurrent readers. Created for review; not a literal depiction "
    "of events."
)

ALT_TEXT = (
    "Panoramic allegorical triptych: the left panel shows institutional "
    "thresholds and origins; the center panel depicts the day's primary struggle "
    "over power and resources; the right panel shows unstable aftermath under dim "
    "light, with small figures moving through labyrinthine architecture."
)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def build_prompt(
    stories: list[dict],
    direction: dict,
    themes: list[dict],
    motifs: list[str] | None = None,
) -> str:
    story_lines = "\n".join(
        f"- Rank {s['rank']}: {s['title']} ({s.get('readers', 0)} readers)"
        for s in stories[:5]
    )
    theme_lines = "\n".join(
        f"- {t['name']}: {t['interpretation']}" for t in themes
    )
    motif_lines = "\n".join(f"- {m}" for m in (motifs or []))
    motif_block = (
        "Concrete motifs drawn from today's specific headlines - make each one "
        "visible and central, rendered as symbolic allegory rather than literal "
        f"reportage:\n{motif_lines}\n\n"
        if motif_lines
        else ""
    )
    avoid = direction.get("avoidRecentMotifs") or []
    avoid_line = (
        "Avoid reusing these recent motifs unless today's reporting makes one "
        f"uniquely necessary: {', '.join(avoid)}.\n"
        if avoid
        else ""
    )
    return (
        f"Create one original 16:9 panoramic triptych oil painting inspired by "
        f"Northern Renaissance detail and Bosch-like symbolic density.\n\n"
        f"Creative direction for {direction.get('date', 'today')}:\n"
        f"- Composition: {direction.get('composition', '')}\n"
        f"- Atmosphere: {direction.get('atmosphere', '')}\n"
        f"- Palette: {direction.get('palette', '')}\n"
        f"- Scale: {direction.get('scale', '')}\n"
        f"- Narrative motion: {direction.get('narrativeMotion', '')}\n"
        f"- Characters: {', '.join(direction.get('characters', []))}\n"
        f"- Symbol families: {', '.join(direction.get('symbolFamilies', []))}\n\n"
        f"Themes to embody:\n{theme_lines}\n\n"
        f"{motif_block}"
        f"Use these Reuters attention signals as allegorical inputs:\n"
        f"{story_lines}\n\n"
        "Triptych structure:\n"
        "- Left panel: origins, institutions, promises, and pressures.\n"
        "- Center panel: primary conflict and active contest for power.\n"
        "- Right panel: consequences, risks, unresolved futures.\n\n"
        "Invent a fresh symbolic vocabulary for this edition. Do not default to "
        "familiar editorial symbols when the direction card offers a less literal "
        "metaphor.\n"
        f"{avoid_line}\n"
        "Hard constraints:\n"
        "- No text, no logos, no Reuters branding, no watermarks.\n"
        "- No photorealistic news scene recreation.\n"
        "- No graphic gore.\n"
        "- Keep all figures symbolic and non-libelous.\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--chartbeat", type=Path)
    parser.add_argument("--direction", type=Path)
    parser.add_argument("--themes", type=Path)
    parser.add_argument("--themes-meta", type=Path)
    args = parser.parse_args()

    run_dir = args.run_dir
    chartbeat_path = args.chartbeat or run_dir / "chartbeat.json"
    direction_path = args.direction or run_dir / "direction.json"
    themes_path = args.themes or run_dir / "themes.json"
    themes_meta_path = args.themes_meta or run_dir / "themes-meta.json"

    missing = [str(p) for p in (chartbeat_path, direction_path, themes_path) if not p.exists()]
    if missing:
        print("Missing inputs: " + ", ".join(missing), file=sys.stderr)
        return 1

    snapshot = read_json(chartbeat_path)
    direction = read_json(direction_path)
    themes = read_json(themes_path)
    motifs: list[str] = []
    if themes_meta_path.exists():
        meta = read_json(themes_meta_path)
        motifs = [str(item) for item in (meta.get("motifs") or [])]
    stories = snapshot.get("stories", [])
    if len(stories) < 5:
        print("Need at least five stories in the snapshot", file=sys.stderr)
        return 1

    prompt = build_prompt(stories, direction, themes, motifs)
    (run_dir / "prompt.txt").write_text(prompt.strip() + "\n", encoding="utf-8")
    (run_dir / "alt.txt").write_text(ALT_TEXT + "\n", encoding="utf-8")
    (run_dir / "caption.md").write_text(DISCLOSURE + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "prompt": str(run_dir / "prompt.txt"),
                "alt": str(run_dir / "alt.txt"),
                "caption": str(run_dir / "caption.md"),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
