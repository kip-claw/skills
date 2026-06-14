---
name: voice-transcribe
title: Voice Transcription
description: Transcribes Telegram voice messages locally with whisper.cpp.
tag: Media
---

# Voice Transcription

When a voice message arrives:

1. Download the OGG file from Telegram to a temp path
2. Run: `{{HOME}}/bin/voice-transcription-runner.sh <path_to_ogg>`
3. Use the stdout output as the user's text input
4. Delete the temp OGG file after transcription

The transcript should be treated as a normal text message from the user.
If transcription fails or produces no output, reply: "I couldn't make
out that voice message — could you try again or type it out?"
