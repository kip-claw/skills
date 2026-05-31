"""Kokoro TTS provider (offline, open-source).

Treats kokoro as a piper-compatible CLI: reads text on stdin, writes wav. If
your kokoro install exposes a different interface, adapt this single file.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


class Provider:
    def __init__(self, config: dict[str, Any]) -> None:
        cfg = config["providers"]["kokoro"]
        self.bin = os.environ.get(cfg.get("bin_env", "KOKORO_BIN")) or shutil.which("kokoro")
        self.voice = os.environ.get(cfg.get("voice_env", "KOKORO_VOICE"))
        if not self.bin or not Path(self.bin).exists():
            raise RuntimeError("kokoro binary not found (set KOKORO_BIN)")
        if not shutil.which("ffmpeg"):
            raise RuntimeError("ffmpeg required for kokoro -> mp3 conversion")

    def synthesize(self, *, text: str, voice: str, speed: float, out_path: Path) -> None:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav:
            wav_path = wav.name
        try:
            cmd = [self.bin, "--out", wav_path]
            if self.voice:
                cmd += ["--voice", self.voice]
            elif voice:
                cmd += ["--voice", voice]
            if abs(speed - 1.0) > 1e-3:
                cmd += ["--speed", f"{speed:.3f}"]
            subprocess.run(cmd, input=text.encode("utf-8"), check=True)
            subprocess.run(
                [
                    "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-i", wav_path, "-c:a", "libmp3lame", "-b:a", "64k",
                    out_path.as_posix(),
                ],
                check=True,
            )
        finally:
            try:
                os.unlink(wav_path)
            except FileNotFoundError:
                pass
