"""OpenAI TTS provider."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any


class Provider:
    def __init__(self, config: dict[str, Any]) -> None:
        cfg = config["providers"]["openai"]
        api_key = os.environ.get(cfg.get("api_key_env", "OPENAI_API_KEY"))
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model = cfg.get("model", "gpt-4o-mini-tts")
        self.fmt = cfg.get("format", "mp3")

    def synthesize(self, *, text: str, voice: str, speed: float, out_path: Path) -> None:
        # The TTS endpoint accepts speed as a 0.25-4.0 multiplier on supported models.
        kwargs: dict[str, Any] = {
            "model": self.model,
            "voice": voice,
            "input": text,
            "response_format": self.fmt,
        }
        if abs(speed - 1.0) > 1e-3:
            kwargs["speed"] = max(0.25, min(4.0, speed))
        with self.client.audio.speech.with_streaming_response.create(**kwargs) as resp:
            resp.stream_to_file(out_path.as_posix())
