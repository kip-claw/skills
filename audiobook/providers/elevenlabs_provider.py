"""ElevenLabs TTS provider."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any


class Provider:
    def __init__(self, config: dict[str, Any]) -> None:
        cfg = config["providers"]["elevenlabs"]
        api_key = os.environ.get(cfg.get("api_key_env", "ELEVENLABS_API_KEY"))
        if not api_key:
            raise RuntimeError("ELEVENLABS_API_KEY not set")
        from elevenlabs.client import ElevenLabs
        self.client = ElevenLabs(api_key=api_key)
        self.model_id = cfg.get("model", "eleven_turbo_v2_5")

    def synthesize(self, *, text: str, voice: str, speed: float, out_path: Path) -> None:
        # Speed is approximated via voice_settings.speed where supported.
        voice_settings = {"speed": float(speed)} if abs(speed - 1.0) > 1e-3 else None
        stream = self.client.text_to_speech.convert(
            voice_id=voice,
            model_id=self.model_id,
            text=text,
            output_format="mp3_44100_64",
            voice_settings=voice_settings,
        )
        with out_path.open("wb") as fh:
            for chunk in stream:
                if chunk:
                    fh.write(chunk)
