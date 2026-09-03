from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image


MODULE_PATH = Path(__file__).parents[1] / "scripts/validate_image.py"
SPEC = importlib.util.spec_from_file_location("validate_image", MODULE_PATH)
assert SPEC and SPEC.loader
validate_image = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validate_image)


def _noise_image(path: Path, width: int, height: int) -> None:
    rng = np.random.default_rng(0)
    array = rng.integers(0, 256, size=(height, width, 3), dtype=np.uint8)
    Image.fromarray(array, "RGB").save(path, "PNG")


def _solid_image(path: Path, width: int, height: int) -> None:
    Image.new("RGB", (width, height), (128, 128, 128)).save(path, "PNG")


def _run(image_path: Path) -> int:
    argv = sys.argv
    sys.argv = ["validate_image.py", "--image", str(image_path)]
    try:
        return validate_image.main()
    finally:
        sys.argv = argv


class ValidateImageTests(unittest.TestCase):
    def test_native_4k_image_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "image.png"
            _noise_image(path, 3840, 2160)
            self.assertEqual(_run(path), 0)
            self.assertEqual(validate_image.validate(path), [])

    def test_square_image_fails_aspect(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "image.png"
            _noise_image(path, 2160, 2160)
            self.assertEqual(_run(path), 1)
            self.assertTrue(
                any("aspect ratio" in p for p in validate_image.validate(path))
            )

    def test_small_image_fails_dimensions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "image.png"
            _noise_image(path, 1536, 1024)
            self.assertEqual(_run(path), 1)
            self.assertTrue(
                any("dimensions must be native 4K" in p for p in validate_image.validate(path))
            )

    def test_blank_image_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "image.png"
            _solid_image(path, 3840, 2160)
            self.assertEqual(_run(path), 1)
            self.assertTrue(
                any("near-blank" in p for p in validate_image.validate(path))
            )

    def test_corrupt_bytes_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "image.png"
            path.write_bytes(b"not a real png" * 8000)
            self.assertEqual(_run(path), 1)
            self.assertTrue(
                any("could not open" in p for p in validate_image.validate(path))
            )

    def test_missing_image_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.png"
            self.assertEqual(_run(path), 1)


if __name__ == "__main__":
    unittest.main()
