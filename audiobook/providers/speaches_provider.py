"""Speaches TTS provider.

Speaches is a self-hosted, OpenAI-API-compatible STT/TTS server running on
Ben's Latitude laptop over Tailscale. This provider calls its
`/v1/audio/speech` endpoint (Kokoro voices) and writes the mp3 response
straight to disk — no local ffmpeg conversion needed.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import httpx

_OPENAI_VOICE_NAMES = {"alloy", "echo", "fable", "onyx", "nova", "shimmer"}


class Provider:
    def __init__(self, config: dict[str, Any]) -> None:
        cfg = config["providers"]["speaches"]
        self.base_url = os.environ.get(cfg.get("base_url_env", "SPEACHES_BASE_URL"), "") or cfg.get(
            "base_url", "http://latitude:8200"
        )
        token_file = Path(
            os.environ.get(cfg.get("token_file_env", "SPEACHES_TOKEN_FILE"), "")
            or cfg.get("token_file", "~/.config/openclaw-speaches/latitude-token")
        ).expanduser()
        if not token_file.exists():
            raise RuntimeError(f"speaches token file not found: {token_file}")
        self.token = token_file.read_text(encoding="utf-8").strip()
        self.model = cfg.get("model", "speaches-ai/Kokoro-82M-v1.0-ONNX")
        self.default_voice = cfg.get("voice", "af_sky")
        self.timeout = float(cfg.get("timeout_seconds", 60))

    def cache_fingerprint(self) -> str:
        return f"speaches:{self.model}:{self.default_voice}"

    def synthesize(self, *, text: str, voice: str, speed: float, out_path: Path) -> None:
        # audiobook.py's global default `voice` is "alloy" (an OpenAI voice
        # name), which isn't a valid Kokoro voice. Fall back to this
        # provider's own configured voice unless the caller passed a real
        # Kokoro voice id (e.g. via --voice af_heart).
        voice_id = voice if voice and voice not in _OPENAI_VOICE_NAMES else self.default_voice
        payload = {
            "model": self.model,
            "input": text,
            "voice": voice_id,
            "response_format": "mp3",
            "speed": speed,
        }
        headers = {"Authorization": f"Bearer {self.token}"}
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(f"{self.base_url.rstrip('/')}/v1/audio/speech", json=payload, headers=headers)
            resp.raise_for_status()
            out_path.write_bytes(resp.content)
