from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


MODULE_PATH = Path(__file__).parents[1] / "scripts/select_image.py"
SPEC = importlib.util.spec_from_file_location("select_image", MODULE_PATH)
assert SPEC and SPEC.loader
select_image = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(select_image)


def _run(run_dir: Path) -> int:
    import sys

    argv = sys.argv
    sys.argv = ["select_image.py", "--run-dir", str(run_dir)]
    try:
        return select_image.main()
    finally:
        sys.argv = argv


class SelectImageTests(unittest.TestCase):
    def test_copies_from_result_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "generated.png"
            source.write_bytes(b"\x89PNG\r\n\x1a\n fake image bytes")
            (root / "image-result.json").write_text(
                json.dumps({"outputs": [{"path": str(source)}]}), encoding="utf-8"
            )
            self.assertEqual(_run(root), 0)
            self.assertTrue((root / "image.png").exists())
            self.assertEqual((root / "image.png").read_bytes(), source.read_bytes())

    def test_empty_image_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            empty = root / "image.png"
            empty.write_bytes(b"")
            (root / "image-result.json").write_text(
                json.dumps({"outputs": [{"path": str(empty)}]}), encoding="utf-8"
            )
            self.assertEqual(_run(root), 1)

    def test_missing_result_falls_back_to_default_image(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "image.png").write_bytes(b"data")
            self.assertEqual(_run(root), 0)

    def test_missing_image_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(_run(root), 1)


if __name__ == "__main__":
    unittest.main()
