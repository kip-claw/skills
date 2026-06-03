---
name: music-import
description: Imports new albums into the NAS beets library and guides staging, duplicate checks, cleanup, and Kodi rescan.
---

# Music Import

The household music library lives on the NAS at
`/srv/dev-disk-by-uuid-a170c673-36d0-4a82-a615-e7356ef68cc6/Music/` and is
managed by beets. The library uses the Kodi-friendly path template
`Artist/Album (Year)/NN - Track.ext` and contains 120+ albums.

When the user wants to add new music — typically Bandcamp zip downloads —
go through `{{HOME}}/bin/nas-music-import.sh`. Do NOT run beets, rsync, unzip,
or sqlite directly; the wrapper script handles all NAS-side operations through
the kip-nas SSH alias.

## The pipeline

The full workflow has six steps. Kip handles 1, 3, 5, and 6. The user
handles 2 and 4 because they involve credentials Kip doesn't have (laptop
SSH keys) and interactive decisions (beets prompts).

1. **User stages files**: User rsyncs zips/folders from their laptop to
   `nas@nas:/srv/dev-disk-by-uuid-a170c673.../bandcamp-import/`.
2. **Kip prepares the staging area**: extract zips into per-album folders.
3. **Kip checks for duplicates** against the existing library.
4. **User runs interactive beets import**. Kip can NOT do this — beets requires
   a human to press A/U/S on each prompt.
5. **Kip cleans up** the staging dir.
6. **Kip triggers Kodi rescan** so new music appears in the Kodi UI.

## When the user mentions buying or downloading new music

The first thing Kip should do is run `status` to see whether anything is
already in the staging dir. The response branches based on what's there:

**If staging is empty or doesn't exist:** Tell the user they need to rsync
their downloads from their laptop first, and give them the exact command:

```
rsync -av --progress --partial \
  --exclude='.DS_Store' --exclude='._*' \
  ~/Downloads/Bandcamp/ \
  nas@nas:/srv/dev-disk-by-uuid-a170c673-36d0-4a82-a615-e7356ef68cc6/bandcamp-import/
```

If the user's Bandcamp downloads aren't in `~/Downloads/Bandcamp/`, ask them
where the new music is on their laptop and adjust the source path. The
destination is always the NAS staging dir above.

Tell them to come back to Kip once the rsync finishes, and you'll handle
the rest.

**If staging already has files in it:** Skip ahead to "process the new music"
below.

## When the user says "the rsync is done" or "process the new music"

1. Run `prepare` to extract any zips
2. Run `check` to flag duplicates of existing library albums
3. If duplicates were found, tell the user — they need to delete one copy
   from staging before importing, otherwise beets will crash mid-operation
4. If no duplicates, give the user this exact command to run:
   ```
   ssh nas@nas
   beet import --noincremental /srv/dev-disk-by-uuid-a170c673-36d0-4a82-a615-e7356ef68cc6/bandcamp-import/
   ```
5. Remind them about the decision rules (see below)

## When the user says "finish the music import"

1. Run `count` first to capture the before-state
2. Run `cleanup` to remove the staging dir
3. Run `rescan` to update Kodi
4. Run `count` again and report how many albums were added

## Commands

**Show what's in staging:**
```
{{HOME}}/bin/nas-music-import.sh status
```

**Extract zips and list ready albums:**
```
{{HOME}}/bin/nas-music-import.sh prepare
```

**Check staged albums against existing library:**
```
{{HOME}}/bin/nas-music-import.sh check
```

**Clean up staging after a successful import:**
```
{{HOME}}/bin/nas-music-import.sh cleanup
```

**Trigger Kodi rescan:**
```
{{HOME}}/bin/nas-music-import.sh rescan
```

**Count albums in beets DB:**
```
{{HOME}}/bin/nas-music-import.sh count
```

## Decision rules for the interactive `beet import` (for user reference)

When prompts come up during `beet import`, the user should press:

- **A** (apply) — match looks right, track titles look correct
- **U** (use as-is) — no good MB match, OR proposed track titles show artist
  names instead of song titles (the "Strata trap" — happens with curated
  compilations like J.PERIOD mixtapes or DJ Amir comps)
- **S** (skip) — uncertain, want to come back to it later
- Bare-folder bootlegs (DBT live recordings, Patterson Hood broadcasts) → **U**
- "This album is already in the library!" prompt → **STOP**, do not press
  Remove old / Keep all / Merge. This is the Bartz-pattern crash; ask Kip.

## Background context

- The `--noincremental` flag is critical. Without it, beets's incremental cache
  silently skips folders it has any prior record of (including past failures),
  refusing to even prompt.
- The bandcamp plugin is enabled in beets's config so it can match bootlegs
  and live recordings that aren't in MusicBrainz.
- Compilations file under `Various Artists/`, which is correct.
- The user's beets config writes the original recording year, not reissue year.
  Old jazz reissues end up filed under their original recording date.
- `cover.jpg`/`cover.png` files in staging after import are normal beets debris
  (the audio files moved out, the art didn't follow). Safe to delete during
  cleanup. Same for PDF booklets.
- The Seagate backup runs nightly at 3am and mirrors the WD. No action needed
  for normal imports — the next 3am sync picks up the new music.

## Notes

- If `cleanup` refuses to run because audio files remain in staging, those are
  imports the user skipped. They can either be re-attempted (back to step 4)
  or deleted manually.
- The user's primary download source is Bandcamp (zips named `Artist - Album.zip`,
  with MP3s and a `cover.jpg` inside). They may also have already-extracted
  folders in the same shape. Both work fine through the same pipeline.
