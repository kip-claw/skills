"""TTS provider registry. Each provider lazily imports its own deps."""
from __future__ import annotations

from importlib import import_module
from typing import Any, Protocol


class TTSProvider(Protocol):
    def synthesize(self, *, text: str, voice: str, speed: float, out_path: Any) -> None: ...


_REGISTRY: dict[str, str] = {
    "openai": "providers.openai_provider",
    "elevenlabs": "providers.elevenlabs_provider",
    "piper": "providers.piper_provider",
    "kokoro": "providers.kokoro_provider",
}


def load_provider(name: str, config: dict[str, Any]) -> TTSProvider:
    if name not in _REGISTRY:
        raise ValueError(f"unknown provider: {name}")
    mod = import_module(_REGISTRY[name])
    return mod.Provider(config=config)  # type: ignore[no-any-return]
