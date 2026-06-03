---
name: nas-storage
description: Manages NAS storage, file transfers, disk usage checks, drive health, and Google Drive sync operations.
---

# NAS Storage

The NAS runs OpenMediaVault on a Pi reachable over Tailscale as `kip-nas`.
All storage operations go through `{{HOME}}/bin/kip-nas.sh`.

The primary drive is the WD (UUID a170c673). The Seagate is a nightly
rsync mirror — do not write to it directly.

When asked about NAS storage, disk usage, or files, always use {{HOME}}/bin/kip-nas.sh rather than running commands like lsblk, df, or ls directly. All NAS operations go through the kip-nas.sh wrapper script.

## Commands

**Check disk usage:**
```
{{HOME}}/bin/kip-nas.sh status
```

**List files (storage root or a subdirectory):**
```
{{HOME}}/bin/kip-nas.sh list [optional/subpath]
```

**Push a file or directory from Kip to NAS:**
```
{{HOME}}/bin/kip-nas.sh push <local-path> [destination-subpath]
```

**Pull a file or directory from NAS to Kip:**
```
{{HOME}}/bin/kip-nas.sh pull <nas-subpath> [local-destination]
```

**Check SMART health on all drives:**
```
{{HOME}}/bin/kip-nas.sh health
```

Interpret SMART output as follows:

- `PASSED` / healthy SMART output: drive health check passed.
- `FAILED` or explicit SMART failure text: alert user via Telegram immediately.
- `SMART_UNAVAILABLE: ...`: telemetry is unavailable (tooling/permissions/USB bridge), not a confirmed drive failure.

When SMART is unavailable, include the reason in summaries (for example: `smartctl not installed`, `sudo requires password`, or `no working transport`) and avoid phrasing it as drive failure.

**Sync Google Drive to NAS:**
```
{{HOME}}/bin/kip-nas.sh sync
```

The Google Drive sync uses rclone on the NAS (configured under the
ben.welsh@gmail.com account) to mirror Drive contents into
`Backups/google-drive/`. Files removed or replaced on Drive are not
deleted locally — they get parked in `Backups/google-drive-archive/<date>/`
so accidental Drive deletions stay recoverable for at least a couple of months.

A typical sync takes ~4 minutes when there's nothing new (just a checksum
scan). Initial syncs or large-change runs can take 15–45 minutes. The sync
also runs automatically on a weekly cron (Sunday 2am — set up separately).

Sync logs land at `~/log/rclone/gdrive-<YYYY-MM-DD>.log` on the NAS. To
check the most recent sync's outcome, look at the last "Errors:" line in
that day's log.

Google Photos is NOT synced via rclone — Google removed the API access in
March 2025. Photos are synced from Google Takeout exports using a dedicated
script (see below).

## Google Photos Sync

Photos from Google Takeout are synced from the laptop to the NAS using:

```
{{HOME}}/bin/kip-photos-sync.py sync
```

The script mounts the laptop's Takeout folder via sshfs, then rsyncs year
folders (2005–2026) and 67 named albums to the NAS Photos directory at
`/mnt/nas-photos/Photos/`. Albums are sorted into year subfolders or
`_unsorted/` based on their content dates.

**Prerequisites:**
- Laptop must be on the same Tailscale network
- Google Takeout export downloaded to `~/Downloads/Takeout/Google Photos` on the laptop

**Commands:**
```
kip-photos-sync.py mount       — mount laptop Takeout via sshfs
kip-photos-sync.py plan        — show what would be synced (dry run)
kip-photos-sync.py sync        — sync all years + albums
kip-photos-sync.py sync-years  — sync only year folders
kip-photos-sync.py sync-albums — sync only named albums
kip-photos-sync.py unmount     — unmount when done
```

The sync is incremental (rsync) — safe to re-run if interrupted. Typical
full sync transfers ~10GB at 6–10 MB/sec over Tailscale.

## Notes

- If the script times out (ConnectTimeout=5), check Tailscale status on both devices
- rsync transfers are resumable — safe to re-run if interrupted
- Drive health: PASSED = fine, FAILED = alert user via Telegram and phone-speak immediately
- `SMART_UNAVAILABLE` means telemetry is unavailable, not failed; report it as an observability gap and include reason text
- Do not write files directly to the Seagate backup drive
