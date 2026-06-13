from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


MODULE_PATH = Path(__file__).parents[1] / "scripts/derive_themes.py"
SPEC = importlib.util.spec_from_file_location("derive_themes", MODULE_PATH)
assert SPEC and SPEC.loader
derive_themes = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(derive_themes)


STORIES = [
    {"rank": 1, "title": "Court weighs landmark ruling", "readers": 900, "sections": ["legal"]},
    {"rank": 2, "title": "Leaders clash over border policy", "readers": 800, "sections": ["world", "politics"]},
    {"rank": 3, "title": "Markets swing on rate fears", "readers": 700, "sections": ["business", "markets"]},
    {"rank": 4, "title": "Title decided in dramatic final", "readers": 600, "sections": ["sports"]},
    {"rank": 5, "title": "New study maps climate risk", "readers": 500, "sections": ["science", "climate"]},
]


class ValidateThemesTests(unittest.TestCase):
    def test_valid_payload_passes(self) -> None:
        payload = [
            {"name": "Law and Judgment", "interpretation": "Courts test accountability.", "storyRanks": [1], "motifs": ["tilted scales"]},
            {"name": "Contested Power", "interpretation": "Leaders maneuver.", "storyRanks": [2], "motifs": ["masked assembly"]},
            {"name": "Markets in Flux", "interpretation": "Capital reacts.", "storyRanks": [3]},
        ]
        themes, motifs = derive_themes.validate_themes(payload, {1, 2, 3, 4, 5})
        self.assertEqual(len(themes), 3)
        self.assertIn("tilted scales", motifs)
        self.assertEqual(themes[0]["storyRanks"], [1])

    def test_unknown_rank_rejected(self) -> None:
        payload = [
            {"name": "A", "interpretation": "x", "storyRanks": [99]},
            {"name": "B", "interpretation": "y", "storyRanks": [1]},
            {"name": "C", "interpretation": "z", "storyRanks": [2]},
        ]
        with self.assertRaises(ValueError):
            derive_themes.validate_themes(payload, {1, 2, 3})

    def test_too_few_themes_rejected(self) -> None:
        payload = [{"name": "A", "interpretation": "x", "storyRanks": [1]}]
        with self.assertRaises(ValueError):
            derive_themes.validate_themes(payload, {1})

    def test_missing_fields_rejected(self) -> None:
        payload = [
            {"name": "", "interpretation": "x", "storyRanks": [1]},
            {"name": "B", "interpretation": "y", "storyRanks": [2]},
            {"name": "C", "interpretation": "z", "storyRanks": [3]},
        ]
        with self.assertRaises(ValueError):
            derive_themes.validate_themes(payload, {1, 2, 3})


class ParseThemesTextTests(unittest.TestCase):
    def test_strips_code_fences(self) -> None:
        text = '```json\n[{"name": "A", "interpretation": "b", "storyRanks": [1]}]\n```'
        data = derive_themes.parse_themes_text(text)
        self.assertEqual(data[0]["name"], "A")

    def test_non_list_rejected(self) -> None:
        with self.assertRaises(ValueError):
            derive_themes.parse_themes_text('{"name": "A"}')


class FallbackTests(unittest.TestCase):
    def test_fallback_is_deterministic_and_cites_real_ranks(self) -> None:
        first, motifs_first = derive_themes.fallback_themes(STORIES, "2026-06-09")
        second, motifs_second = derive_themes.fallback_themes(STORIES, "2026-06-09")
        self.assertEqual(first, second)
        self.assertEqual(motifs_first, motifs_second)
        self.assertGreaterEqual(len(first), derive_themes.MIN_THEMES)
        self.assertLessEqual(len(first), derive_themes.MAX_THEMES)
        valid = {s["rank"] for s in STORIES}
        for theme in first:
            self.assertTrue(theme["storyRanks"])
            self.assertTrue(set(theme["storyRanks"]) <= valid)

    def test_fallback_motifs_track_headline_content(self) -> None:
        war = [
            {"rank": 1, "title": "Missile strike hits border city", "readers": 900, "sections": ["world"]},
            {"rank": 2, "title": "Troops clash near front line", "readers": 800, "sections": ["world"]},
            {"rank": 3, "title": "Navy fleet deploys to strait", "readers": 700, "sections": ["world"]},
            {"rank": 4, "title": "Oil prices surge on supply fear", "readers": 600, "sections": ["business"]},
            {"rank": 5, "title": "Markets fall on war jitters", "readers": 500, "sections": ["markets"]},
        ]
        weather = [
            {"rank": 1, "title": "Flood swallows river town", "readers": 900, "sections": ["science"]},
            {"rank": 2, "title": "Wildfire spreads through dry hills", "readers": 800, "sections": ["science"]},
            {"rank": 3, "title": "Drought ruins the season harvest", "readers": 700, "sections": ["science"]},
            {"rank": 4, "title": "Vaccine slows measles outbreak", "readers": 600, "sections": ["health"]},
            {"rank": 5, "title": "Glacier ice retreats further", "readers": 500, "sections": ["climate"]},
        ]
        _, war_motifs = derive_themes.fallback_themes(war, "2026-06-09")
        _, weather_motifs = derive_themes.fallback_themes(weather, "2026-06-09")
        self.assertTrue(war_motifs)
        self.assertTrue(weather_motifs)
        # Different headlines must yield different motifs (content-driven).
        self.assertNotEqual(set(war_motifs), set(weather_motifs))
        # No motif may come from a fixed, news-agnostic pool: every motif here
        # must trace to a topic actually present in that day's stories.
        self.assertTrue(
            any("vessel" in m or "strait" in m or "rampart" in m for m in war_motifs)
        )
        self.assertTrue(
            any("water" in m or "ember" in m or "riverbed" in m for m in weather_motifs)
        )

    def test_main_force_fallback_writes_themes_and_meta(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            chartbeat = root / "chartbeat.json"
            direction = root / "direction.json"
            output = root / "themes.json"
            chartbeat.write_text(
                json.dumps({"retrievedAt": "2026-06-09T00:00:00Z", "stories": STORIES}),
                encoding="utf-8",
            )
            direction.write_text(json.dumps({"date": "2026-06-09"}), encoding="utf-8")
            import sys

            argv = sys.argv
            sys.argv = [
                "derive_themes.py",
                "--chartbeat", str(chartbeat),
                "--direction", str(direction),
                "--output", str(output),
                "--force-fallback",
            ]
            try:
                rc = derive_themes.main()
            finally:
                sys.argv = argv
            self.assertEqual(rc, 0)
            themes = json.loads(output.read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(themes), derive_themes.MIN_THEMES)
            meta = json.loads((root / "themes-meta.json").read_text(encoding="utf-8"))
            self.assertEqual(meta["themeSource"], "fallback")
            self.assertTrue(meta["motifs"])


if __name__ == "__main__":
    unittest.main()
