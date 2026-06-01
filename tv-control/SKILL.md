---
name: tv-control
description: Controls TV, Yamaha receiver, and Kodi playback for music, video, photos, announcements, and power actions.
---

# TV and Media Control

Kip is connected to a Yamaha RX-V379 receiver and Samsung TV via HDMI.

Kodi runs on Kip and serves media from the NAS. All control goes through
`{{HOME}}/bin/kip-tv.sh`.

## Commands

**Turn receiver on and switch to Kip's input:**
```
{{HOME}}/bin/kip-tv.sh on
```

**Turn receiver off (standby):**
```
{{HOME}}/bin/kip-tv.sh off
```

**Play music (shuffled library or search):**
```
{{HOME}}/bin/kip-tv.sh play-music
{{HOME}}/bin/kip-tv.sh play-music "search query"
```

**Play a video:**
```
{{HOME}}/bin/kip-tv.sh play-video "title"
```

**Start photo slideshow:**
```
{{HOME}}/bin/kip-tv.sh slideshow
```

**Stop playback:**
```
{{HOME}}/bin/kip-tv.sh stop
```

**Pause/resume:**
```
{{HOME}}/bin/kip-tv.sh pause
```

**Set volume (0-100):**
```
{{HOME}}/bin/kip-tv.sh volume 100
```

**Speak through the sound system:**
```
{{HOME}}/bin/kip-tv.sh say "text to speak"
```

## Notes

- Kodi volume should always be at 100 — use the receiver's volume knob for listening volume
- The `say` command speaks through the HDMI sound system
- Use phone-speak as fallback when the TV/receiver is off
- Kodi web interface: http://192.168.0.125:8080 (user: kodi, pass: kodi)
- Log: /var/log/kip-tv.log
