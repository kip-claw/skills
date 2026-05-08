---
name: voice-transcribe
description: >
  Transcribes Telegram voice messages locally using whisper.cpp.
  Use when the user sends a voice message or audio note. Download
  the voice file, run transcription, and treat the resulting text
  as the user's message.
---

# Voice Transcription

When a voice message arrives:

1. Download the OGG file from Telegram to a temp path
2. Run: `{{HOME}}/bin/transcribe_voice.sh <path_to_ogg>`
3. Use the stdout output as the user's text input
4. Delete the temp OGG file after transcription

The transcript should be treated as a normal text message from the user.
If transcription fails or produces no output, reply: "I couldn't make
out that voice message — could you try again or type it out?"
