from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import unittest


MODULE_PATH = Path(__file__).parents[1] / "scripts/publish_to_site.py"
SPEC = importlib.util.spec_from_file_location("publish_to_site", MODULE_PATH)
assert SPEC and SPEC.loader
publish_to_site = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publish_to_site)


class PushWithRetryTests(unittest.TestCase):
    def test_succeeds_after_transient_failures(self) -> None:
        calls: list[list[str]] = []
        failures = {"count": 2}

        def fake_run(command: list[str], cwd: Path) -> None:
            calls.append(command)
            if command[:2] == ["git", "push"] and failures["count"] > 0:
                failures["count"] -= 1
                raise subprocess.CalledProcessError(1, command)

        original_run = publish_to_site.run
        original_sleep = publish_to_site.time.sleep
        publish_to_site.run = fake_run
        publish_to_site.time.sleep = lambda _seconds: None
        try:
            publish_to_site.push_with_retry(Path("/tmp/repo"), attempts=4)
        finally:
            publish_to_site.run = original_run
            publish_to_site.time.sleep = original_sleep

        pushes = [c for c in calls if c[:2] == ["git", "push"]]
        pulls = [c for c in calls if c[:2] == ["git", "pull"]]
        self.assertEqual(len(pushes), 3)
        self.assertEqual(len(pulls), 3)

    def test_raises_after_exhausting_attempts(self) -> None:
        def always_fail(command: list[str], cwd: Path) -> None:
            if command[:2] == ["git", "push"]:
                raise subprocess.CalledProcessError(1, command)

        original_run = publish_to_site.run
        original_sleep = publish_to_site.time.sleep
        publish_to_site.run = always_fail
        publish_to_site.time.sleep = lambda _seconds: None
        try:
            with self.assertRaises(subprocess.CalledProcessError):
                publish_to_site.push_with_retry(Path("/tmp/repo"), attempts=3)
        finally:
            publish_to_site.run = original_run
            publish_to_site.time.sleep = original_sleep


class PublishPreconditionTests(unittest.TestCase):
    @staticmethod
    def _init_repo(path: Path) -> None:
        subprocess.run(["git", "init", "-q", str(path)], check=True)
        subprocess.run(["git", "-C", str(path), "checkout", "-q", "-b", "main"], check=True)
        subprocess.run(
            ["git", "-C", str(path), "config", "user.email", "t@example.com"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(path), "config", "user.name", "Test"], check=True
        )
        (path / "seed.txt").write_text("seed", encoding="utf-8")
        subprocess.run(["git", "-C", str(path), "add", "seed.txt"], check=True)
        subprocess.run(
            ["git", "-C", str(path), "commit", "-q", "-m", "seed"], check=True
        )

    def test_clean_main_passes(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            self._init_repo(repo)
            publish_to_site.assert_publish_preconditions(repo)

    def test_wrong_branch_fails(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            self._init_repo(repo)
            subprocess.run(
                ["git", "-C", str(repo), "checkout", "-q", "-b", "feature"], check=True
            )
            with self.assertRaises(ValueError):
                publish_to_site.assert_publish_preconditions(repo)

    def test_staged_changes_fail(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            self._init_repo(repo)
            (repo / "extra.txt").write_text("unrelated", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "extra.txt"], check=True)
            with self.assertRaises(ValueError):
                publish_to_site.assert_publish_preconditions(repo)


if __name__ == "__main__":
    unittest.main()
