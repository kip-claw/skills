#!/usr/bin/env python3
"""Create a deterministic daily art-direction card with repetition controls."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import random

CHARACTERS = [
    "pilgrims and wayfarers",
    "merchants and market keepers",
    "artisans and instrument makers",
    "masked magistrates",
    "courtiers and heralds",
    "gardeners and field workers",
    "sailors and navigators",
    "scholars and alchemists",
    "players on a theatrical stage",
    "hybrid human-machine attendants",
]

SYMBOL_FAMILIES = [
    "gardens, seeds, roots, grafts, and strange fruit",
    "vessels, canals, wells, floods, and bridges",
    "games, dice, wheels, races, and balancing acts",
    "musical instruments, choirs, bells, and broken harmonies",
    "feasts, kitchens, ovens, tables, and empty bowls",
    "labyrinths, thresholds, ladders, tunnels, and hidden chambers",
    "celestial bodies, eclipses, comets, clocks, and constellations",
    "workshops, looms, mills, gears, and unfinished machines",
    "animals, insects, shells, nests, and migrating flocks",
    "theaters, masks, puppets, curtains, and processions",
    "books, maps, mirrors, lenses, and cabinets of curiosities",
    "ruins, scaffolds, towers, arches, and impossible dwellings",
]

COMPOSITIONS = [
    "three balanced panels with one recurring object crossing every boundary",
    "a low viewpoint with monumental foreground figures and distant miniature worlds",
    "a high bird's-eye view with winding paths connecting all three panels",
    "an asymmetrical triptych with a quiet left panel and an overflowing center-right",
    "three nested circular arenas embedded across the triptych",
    "a continuous procession moving through all three panels",
    "a central vertical axis surrounded by mirrored but imperfect side panels",
    "deep theatrical prosceniums, each panel revealing a scene behind another scene",
]

ATMOSPHERES = [
    "clear winter light with long blue shadows",
    "humid summer haze before a storm",
    "moonlit silver-blue night with small pools of firelight",
    "festival daylight gradually darkening into an eclipse",
    "misty dawn with luminous clouds and wet reflective ground",
    "dry ochre heat under a pale, nearly colorless sky",
    "green-gold twilight after rain",
    "cold starlight with aurora-like veils",
]

PALETTES = [
    "verdigris, lapis, ochre, parchment, burgundy, and restrained gold",
    "earth umber, moss green, bone white, rust red, and smoky blue",
    "pearl gray, faded rose, malachite, saffron, and ink black",
    "moonlit indigo, silver, chalk white, ember orange, and muted violet",
    "dry clay, straw yellow, olive, turquoise, and dark crimson",
    "limited grisaille with selective jewel-toned red, blue, and green accents",
    "spring green, river blue, coral, cream, and weathered copper",
    "deep forest green, plum, old gold, pale cyan, and soot",
]

SCALES = [
    "mostly miniature crowds with three oversized symbolic objects",
    "alternating intimate foreground vignettes and immense distant structures",
    "tiny figures navigating architecture that behaves like a living organism",
    "monumental characters surrounded by miniature consequences",
    "many equal-sized vignettes with no single heroic protagonist",
    "a gradual shift from human scale to cosmic scale across the panels",
]

MOTIONS = [
    "a pilgrimage from promise through appetite to consequence",
    "several stories colliding simultaneously rather than unfolding in sequence",
    "a cycle in which the right panel visually feeds back into the left",
    "a procession repeatedly interrupted by side scenes and countercurrents",
    "mirrored actions whose meanings reverse from one panel to the next",
    "a rising visual rhythm from quiet observation to crowded disorder",
]

DEFAULT_RECENT_MOTIFS = [
    "border gates",
    "balanced scales",
    "crowns",
    "masked clerks",
    "fraying banners",
    "mechanical birds",
]


def choose_many(rng: random.Random, values: list[str], count: int) -> list[str]:
    return rng.sample(values, k=count)


def recent_motifs(root: Path, limit: int) -> list[str]:
    manifests = sorted(root.glob("*/manifest.json"), reverse=True)
    motifs: list[str] = []
    for path in manifests[:limit]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        motifs.extend(str(item) for item in data.get("motifsUsed", []))
    if not motifs:
        motifs = DEFAULT_RECENT_MOTIFS.copy()
    return list(dict.fromkeys(motifs))


def build_card(run_date: str, root: Path, recent_limit: int) -> dict:
    seed = int(hashlib.sha256(run_date.encode("ascii")).hexdigest()[:16], 16)
    rng = random.Random(seed)
    return {
        "schemaVersion": 1,
        "date": run_date,
        "seed": seed,
        "characters": choose_many(rng, CHARACTERS, 2),
        "symbolFamilies": choose_many(rng, SYMBOL_FAMILIES, 3),
        "composition": rng.choice(COMPOSITIONS),
        "atmosphere": rng.choice(ATMOSPHERES),
        "palette": rng.choice(PALETTES),
        "scale": rng.choice(SCALES),
        "narrativeMotion": rng.choice(MOTIONS),
        "avoidRecentMotifs": recent_motifs(root, recent_limit),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--runs-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--recent-runs", type=int, default=7)
    args = parser.parse_args()

    date.fromisoformat(args.date)
    card = build_card(args.date, args.runs_root, args.recent_runs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(card, ensure_ascii=True, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"output": str(args.output), "seed": card["seed"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
