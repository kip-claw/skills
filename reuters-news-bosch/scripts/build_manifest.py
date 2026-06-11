#!/usr/bin/env python3
"""Build provenance and review files for a Reuters News Bosch run."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--prompt-file", type=Path, required=True)
    parser.add_argument("--themes-file", type=Path, required=True)
    parser.add_argument("--direction-file", type=Path, required=True)
    parser.add_argument("--alt-file", type=Path, required=True)
    parser.add_argument("--caption-file", type=Path, required=True)
    parser.add_argument(
        "--motif",
        action="append",
        default=[],
        help="Concrete motif visible in the reviewed image; repeat as needed.",
    )
    parser.add_argument("--provider", default="openclaw image_generate")
    parser.add_argument(
        "--theme-source",
        default="unknown",
        help="How themes were derived: 'model' or 'fallback'.",
    )
    parser.add_argument(
        "--theme-model",
        default=None,
        help="Model that produced the themes, when source is 'model'.",
    )
    parser.add_argument(
        "--meta-file",
        type=Path,
        default=None,
        help="themes-meta.json with themeSource, model, and motifs; overrides flags when present.",
    )
    args = parser.parse_args()

    source_path = args.run_dir / "chartbeat.json"
    image_path = args.run_dir / "image.png"
    required = [
        source_path,
        image_path,
        args.prompt_file,
        args.themes_file,
        args.direction_file,
        args.alt_file,
        args.caption_file,
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        print("Missing artifacts: " + ", ".join(missing), file=sys.stderr)
        return 1

    source = read_json(source_path)
    themes = read_json(args.themes_file)
    direction = read_json(args.direction_file)

    theme_source = args.theme_source
    theme_model = args.theme_model
    motifs = list(args.motif)
    if args.meta_file and args.meta_file.exists():
        meta = read_json(args.meta_file)
        theme_source = meta.get("themeSource", theme_source)
        theme_model = meta.get("model", theme_model)
        if not motifs:
            motifs = [str(item) for item in meta.get("motifs", [])]

    ranks = {story["rank"] for story in source["stories"]}
    for theme in themes:
        cited = set(theme.get("storyRanks", []))
        if not cited or not cited <= ranks:
            print(f"Invalid story ranks for theme: {theme.get('name')}", file=sys.stderr)
            return 1

    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    manifest = {
        "schemaVersion": 1,
        "generatedAt": generated_at,
        "disclosure": (
            "AI-generated editorial artwork based on a point-in-time ranking "
            "of Reuters stories drawing the most concurrent readers."
        ),
        "imageProvider": args.provider,
        "themeSource": theme_source,
        "themeModel": theme_model,
        "sourceSnapshot": "chartbeat.json",
        "sourceRetrievedAt": source["retrievedAt"],
        "metric": source["metric"],
        "storyCount": len(source["stories"]),
        "themes": themes,
        "creativeDirection": direction,
        "motifsUsed": sorted(set(motifs)),
        "prompt": args.prompt_file.read_text(encoding="utf-8").strip(),
        "artifacts": {
            "image": "image.png",
            "alt": "alt.txt",
            "caption": "caption.md",
            "preview": "preview.md",
        },
    }
    (args.run_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=True, indent=2) + "\n", encoding="utf-8"
    )

    story_lines = [
        f"{story['rank']}. {story['title']} ({story['readers']:,} readers)"
        for story in source["stories"]
    ]
    theme_lines = [
        f"- **{theme['name']}**: {theme['interpretation']} "
        f"(stories {', '.join(map(str, theme['storyRanks']))})"
        for theme in themes
    ]
    preview = "\n".join(
        [
            "# Reuters News Bosch Trial",
            "",
            manifest["disclosure"],
            "",
            f"Chartbeat snapshot: {source['retrievedAt']}",
            "",
            "## Themes",
            "",
            *theme_lines,
            "",
            "## Creative Direction",
            "",
            f"- Characters: {', '.join(direction['characters'])}",
            f"- Symbols: {', '.join(direction['symbolFamilies'])}",
            f"- Composition: {direction['composition']}",
            f"- Atmosphere: {direction['atmosphere']}",
            f"- Palette: {direction['palette']}",
            f"- Scale: {direction['scale']}",
            f"- Narrative motion: {direction['narrativeMotion']}",
            "",
            "## Ranked Stories",
            "",
            *story_lines,
            "",
            "## Caption",
            "",
            args.caption_file.read_text(encoding="utf-8").strip(),
            "",
            "## Alt Text",
            "",
            args.alt_file.read_text(encoding="utf-8").strip(),
            "",
        ]
    )
    (args.run_dir / "preview.md").write_text(preview, encoding="utf-8")
    print(json.dumps({"manifest": str(args.run_dir / "manifest.json")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
