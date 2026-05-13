---
name: nas-storage
description: Manages NAS storage, file transfers, disk usage checks, drive health, Google Drive sync, and Cloudflare R2 offsite backup operations.
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
March 2025. Photos archives are handled separately via Google Takeout.

**Offsite backup to Cloudflare R2:**
```
{{HOME}}/bin/kip-nas.sh r2-sync
```

The R2 offsite backup uses `rclone copy` (not sync) to upload the entire WD
drive to Cloudflare R2 (`r2-backup:kip-nas-backup` bucket, Infrequent Access
tier). Because it uses `copy`, files deleted on the NAS are preserved on R2 —
this is intentional for disaster recovery.

The sync is bandwidth-limited to 10 MB/s (`--bwlimit 10M`) to avoid
saturating the Pi's connection. Initial sync of ~517GB will take many hours;
subsequent runs are incremental and fast (checksum-based).

R2 sync runs automatically on a weekly cron (Wednesday 3am — offset from the
Google Drive sync on Sunday 2am). Logs land at
`~/log/rclone/r2-<YYYY-MM-DD>.log` on the NAS.

## Notes

- If the script times out (ConnectTimeout=5), check Tailscale status on both devices
- rsync transfers are resumable — safe to re-run if interrupted
- Drive health: PASSED = fine, FAILED = alert user via Telegram and phone-speak immediately
- Do not write files directly to the Seagate backup drive
