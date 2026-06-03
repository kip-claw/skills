---
name: pi-diagnostics
description: Query, review, or run Pi and OpenClaw diagnostics. Use when asked about Pi health, system temperatures, disk usage, cron job status, OpenClaw job history, or OpenClaw config snapshots.
metadata: {"openclaw": {"emoji": "🖥️", "requires": {"bins": ["gog"]}}}
---

# Pi Diagnostics (Google Sheets)

Manages Pi hardware health, cron job health, OpenClaw job status, and OpenClaw config snapshots in a single Google Sheet with four tabs:
- **Diagnostics Sheet:** `https://docs.google.com/spreadsheets/d/1xIMil5RtrnrHwRORIaV9wMJQPsvXDlDdyfVBiNmhBhI/edit`

## Sheet Structure

### Tab 1: Pi Health
Columns: `Timestamp`, `CPU Temp (°C)`, `GPU Temp (°C)`, `CPU Load (1m)`, `CPU Load (5m)`, `CPU Load (15m)`, `RAM Used (MB)`, `RAM Total (MB)`, `Disk Used (GB)`, `Disk Total (GB)`, `Uptime (days)`

### Tab 2: Cron Health
Columns: `Timestamp`, `Script`, `Exit Code`, `Duration (s)`, `Notes`

Populated automatically by the exit trap in each bin script via `kip-cron-log.sh`.

### Tab 3: OpenClaw Jobs
Columns: `Timestamp`, `Job Name`, `Status`, `Duration (s)`, `Consecutive Errors`, `Error Reason`, `Notes`

Populated by `openclaw-jobs-snapshot.sh` (daily snapshot of `~/.openclaw/cron/jobs-state.json`).

### Tab 4: OpenClaw Config
Columns: `Timestamp`, `Version`, `Primary Model`, `Agent Runtime`, `Memory Search Provider`, `Memory Search Model`, `Skills Count`, `Gateway Mode`, `Notes`

Populated by `openclaw-config-snapshot.sh` (daily snapshot of `openclaw.json` + `update-check.json`).

## Collection Scripts

| Script | Frequency | Logs to |
|---|---|---|
| `system-pi-health-report.sh` | Every 6 hours | Pi Health tab + `kip-claw/src/lib/piHealth.json` |
| `openclaw-jobs-snapshot.sh` | Daily at 4:00am | OpenClaw Jobs tab + `kip-claw/src/lib/openclawJobs.json` |
| `openclaw-config-snapshot.sh` | Daily at 4:15am | OpenClaw Config tab + `kip-claw/src/lib/openclawConfig.json` |
| `kip-cron-log.sh` | On every bin script exit | Cron Health tab |

## Commands

### Query latest Pi health readings

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets get 1xIMil5RtrnrHwRORIaV9wMJQPsvXDlDdyfVBiNmhBhI "Pi Health!A1:K10" --json
```

### Query recent cron health

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets get 1xIMil5RtrnrHwRORIaV9wMJQPsvXDlDdyfVBiNmhBhI "Cron Health!A1:E20" --json
```

### Query OpenClaw job statuses

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets get 1xIMil5RtrnrHwRORIaV9wMJQPsvXDlDdyfVBiNmhBhI "OpenClaw Jobs!A1:G20" --json
```

### Query OpenClaw config history

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets get 1xIMil5RtrnrHwRORIaV9wMJQPsvXDlDdyfVBiNmhBhI "OpenClaw Config!A1:I10" --json
```

### Manually trigger a Pi health snapshot

```bash
bash {{HOME}}/bin/system-pi-health-report.sh
```

### Manually trigger an OpenClaw jobs snapshot

```bash
bash {{HOME}}/bin/openclaw-jobs-snapshot.sh
```

### Manually trigger an OpenClaw config snapshot

```bash
bash {{HOME}}/bin/openclaw-config-snapshot.sh
```

## Notes

- Sheet ID: `1xIMil5RtrnrHwRORIaV9wMJQPsvXDlDdyfVBiNmhBhI`
- Tabs: `Pi Health`, `Cron Health`, `OpenClaw Jobs`, `OpenClaw Config`
- Requires `gog` with Sheets API access (service-level account context is preconfigured)
- kip-claw JSON mirrors: `src/lib/piHealth.json`, `src/lib/openclawJobs.json`, `src/lib/openclawConfig.json`
- GPU temp requires `vcgencmd` (available on Raspberry Pi OS); will be empty on non-Pi hardware
- Cron Health rows are appended by `kip-cron-log.sh`, which is called via exit traps in: `kip-backup`, `kip-batocera-backup`, `kip-speedtest`, `kip-pi-health`, `kip-openclaw-jobs`, `kip-openclaw-config`
