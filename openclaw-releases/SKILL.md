---
name: openclaw-release-check
description: Check for new OpenClaw package releases and notify the user when an update is available.
metadata: {"openclaw": {"emoji": "📦"}}
---

# OpenClaw Release Check

Monitors for new releases of the `openclaw` npm package and notifies the user when an update is available.

## Command

```bash
bash {{HOME}}/bin/kip-openclaw-release-check.sh
```

## Exit Codes

- **0**: A new version is available. The script prints JSON with `current`, `latest`, and `update_available` fields.
- **2**: Already on the latest version. No notification needed.
- **1**: Error determining versions.

## Behavior

Run the check command. Parse the JSON output.

- If exit code is **0** (update available): Send the user a message like:
  > 📦 OpenClaw update available: **v{latest}** (currently running **v{current}**).
  > Update with: `npm install -g openclaw@latest`

- If exit code is **2** (up to date): No message needed. Only mention it if the user explicitly asked for a check.

- If exit code is **1** (error): Let the user know the check failed and include the error output.

## Schedule

This skill should run once daily (8:00 AM). Only notify the user when there is actually a new version — do not send "you're up to date" messages on scheduled runs.

## Manual Use

The user may also ask things like:
- "Is there a new version of openclaw?"
- "Check for openclaw updates"
- "What version of openclaw am I running?"

For manual requests, always report the result regardless of whether an update is available.

## Notes

- Requires `openclaw` and `npm` on PATH
- The current version comes from `openclaw --version`
- The latest version comes from the npm registry via `npm view openclaw version`
