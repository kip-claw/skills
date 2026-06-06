from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


MODULE_PATH = Path(__file__).parents[1] / "scripts/direction_card.py"
SPEC = importlib.util.spec_from_file_location("direction_card", MODULE_PATH)
assert SPEC and SPEC.loader
direction_card = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(direction_card)


class DirectionCardTests(unittest.TestCase):
    def test_same_date_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = direction_card.build_card("2026-06-06", root, 7)
            second = direction_card.build_card("2026-06-06", root, 7)
            self.assertEqual(first, second)

    def test_different_dates_vary_direction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = direction_card.build_card("2026-06-06", root, 7)
            second = direction_card.build_card("2026-06-07", root, 7)
            fields = (
                "characters",
                "symbolFamilies",
                "composition",
                "atmosphere",
                "palette",
                "scale",
                "narrativeMotion",
            )
            self.assertTrue(any(first[field] != second[field] for field in fields))

    def test_recent_manifest_motifs_are_avoided(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = root / "2026-06-05-120000"
            run.mkdir()
            (run / "manifest.json").write_text(
                json.dumps({"motifsUsed": ["glass orchard", "spiral bridge"]}),
                encoding="utf-8",
            )
            card = direction_card.build_card("2026-06-06", root, 7)
            self.assertEqual(
                card["avoidRecentMotifs"], ["glass orchard", "spiral bridge"]
            )


if __name__ == "__main__":
    unittest.main()
