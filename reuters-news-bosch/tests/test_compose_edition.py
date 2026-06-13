from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


MODULE_PATH = Path(__file__).parents[1] / "scripts/compose_edition.py"
SPEC = importlib.util.spec_from_file_location("compose_edition", MODULE_PATH)
assert SPEC and SPEC.loader
compose_edition = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(compose_edition)


STORIES = [
    {"rank": 1, "title": "Court weighs landmark ruling", "readers": 900, "sections": ["legal"]},
    {"rank": 2, "title": "Leaders clash over border policy", "readers": 800, "sections": ["world"]},
    {"rank": 3, "title": "Markets swing on rate fears", "readers": 700, "sections": ["business"]},
    {"rank": 4, "title": "Title decided in dramatic final", "readers": 600, "sections": ["sports"]},
    {"rank": 5, "title": "New study maps climate risk", "readers": 500, "sections": ["science"]},
]
DIRECTION = {
    "date": "2026-06-09",
    "composition": "three balanced panels",
    "atmosphere": "clear winter light",
    "palette": "verdigris and ochre",
    "scale": "miniature crowds",
    "narrativeMotion": "a pilgrimage",
    "characters": ["pilgrims", "merchants"],
    "symbolFamilies": ["gardens", "vessels"],
    "avoidRecentMotifs": ["border gates", "crowns"],
}
THEMES = [
    {"name": "Law and Judgment", "interpretation": "Courts test accountability.", "storyRanks": [1]},
    {"name": "Contested Power", "interpretation": "Leaders maneuver.", "storyRanks": [2]},
    {"name": "Markets in Flux", "interpretation": "Capital reacts.", "storyRanks": [3]},
]


def _setup(root: Path) -> Path:
    (root / "chartbeat.json").write_text(
        json.dumps({"retrievedAt": "2026-06-09T00:00:00Z", "stories": STORIES}),
        encoding="utf-8",
    )
    (root / "direction.json").write_text(json.dumps(DIRECTION), encoding="utf-8")
    (root / "themes.json").write_text(json.dumps(THEMES), encoding="utf-8")
    return root


class ComposeEditionTests(unittest.TestCase):
    def test_build_prompt_includes_themes_and_avoids(self) -> None:
        prompt = compose_edition.build_prompt(STORIES, DIRECTION, THEMES)
        self.assertIn("Law and Judgment", prompt)
        self.assertIn("border gates", prompt)
        self.assertIn("fresh symbolic vocabulary", prompt)
        self.assertIn("No text, no logos", prompt)

    def test_main_is_deterministic(self) -> None:
        import sys

        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            outputs = []
            for directory in (d1, d2):
                root = _setup(Path(directory))
                argv = sys.argv
                sys.argv = ["compose_edition.py", "--run-dir", str(root)]
                try:
                    rc = compose_edition.main()
                finally:
                    sys.argv = argv
                self.assertEqual(rc, 0)
                outputs.append((root / "prompt.txt").read_text(encoding="utf-8"))
            self.assertEqual(outputs[0], outputs[1])

    def test_main_writes_all_artifacts(self) -> None:
        import sys

        with tempfile.TemporaryDirectory() as directory:
            root = _setup(Path(directory))
            argv = sys.argv
            sys.argv = ["compose_edition.py", "--run-dir", str(root)]
            try:
                rc = compose_edition.main()
            finally:
                sys.argv = argv
            self.assertEqual(rc, 0)
            for name in ("prompt.txt", "alt.txt", "caption.md"):
                self.assertTrue((root / name).exists())

    def test_main_injects_headline_motifs(self) -> None:
        import sys

        with tempfile.TemporaryDirectory() as directory:
            root = _setup(Path(directory))
            (root / "themes-meta.json").write_text(
                json.dumps(
                    {
                        "themeSource": "fallback",
                        "motifs": ["a listing vessel taking on dark water"],
                    }
                ),
                encoding="utf-8",
            )
            argv = sys.argv
            sys.argv = ["compose_edition.py", "--run-dir", str(root)]
            try:
                rc = compose_edition.main()
            finally:
                sys.argv = argv
            self.assertEqual(rc, 0)
            prompt = (root / "prompt.txt").read_text(encoding="utf-8")
            self.assertIn("a listing vessel taking on dark water", prompt)
            self.assertIn("Concrete motifs drawn from today's specific headlines", prompt)


if __name__ == "__main__":
    unittest.main()
