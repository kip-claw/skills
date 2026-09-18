---
name: voice-transcribe
title: Voice Transcription
description: Transcribes Telegram voice messages with a private Speaches (faster-whisper) service on Ben's Latitude over Tailscale.
tag: Media
---

# Voice Transcription

Telegram voice messages are transcribed by a token-authenticated Speaches (faster-whisper) service on Ben's Latitude — the same self-hosted server that provides the `audiobook` skill's TTS. The Pi converts audio transiently and sends it only over Tailscale; it has no local Whisper fallback.

When a voice message arrives:

1. Download the OGG file from Telegram to a temp path.
2. Run: `{{HOME}}/bin/voice-transcription-runner.sh <path_to_ogg>`.
3. Use the stdout output as the user's text input.
4. Delete the temp OGG file after transcription.

The transcript should be treated as a normal text message from the user.
If transcription fails or produces no output, reply: "I couldn't make
out that voice message — could you try again or type it out?"
