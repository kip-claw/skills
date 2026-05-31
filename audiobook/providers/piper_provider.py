"""Piper TTS provider (offline, CPU-friendly; recommended Pi fallback).

Pipes text -> `piper` -> wav -> ffmpeg -> mp3. Assumes `piper` binary and a
voice model on disk. See: https://github.com/rhasspy/piper
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
        cfg = config["providers"]["piper"]
        self.bin = os.environ.get(cfg.get("bin_env", "PIPER_BIN")) or shutil.which("piper")
        self.voice = os.environ.get(cfg.get("voice_env", "PIPER_VOICE"))
        self.sample_rate = int(cfg.get("sample_rate", 22050))
        if not self.bin or not Path(self.bin).exists():
            raise RuntimeError("piper binary not found (set PIPER_BIN or install piper)")
        if not self.voice or not Path(self.voice).exists():
            raise RuntimeError("piper voice model not found (set PIPER_VOICE)")
        if not shutil.which("ffmpeg"):
            raise RuntimeError("ffmpeg required to convert piper wav to mp3")

    def cache_fingerprint(self) -> str:
        # Piper ignores the abstract `voice` arg — the actual narration is
        # whatever PIPER_VOICE points at. Include the resolved model path in
        # the cache key so swapping voices doesn't return stale fragments.
        return f"piper:{Path(self.voice).resolve().as_posix()}"

    def synthesize(self, *, text: str, voice: str, speed: float, out_path: Path) -> None:
        # piper ignores the `voice` arg (voice = model file). speed via length_scale.
        length_scale = 1.0 / max(0.25, float(speed))
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav:
            wav_path = wav.name
        try:
            cmd = [
                self.bin,
                "--model", self.voice,
                "--output_file", wav_path,
                "--length_scale", f"{length_scale:.3f}",
            ]
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
