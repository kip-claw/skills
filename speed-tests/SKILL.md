---
name: speed-test
description: Runs an internet speed test, logs to Google Sheets, and updates kip-claw speedTests.json for public stats.
---

# Internet Speed Test

Runs a speed test, logs results to the Internet Speed Log Google Sheet, and exports
the latest result to kip-claw JSON data for the public stats page.

## Command

```
{{HOME}}/bin/kip-speedtest.sh
```

## Sheet

Results are logged to:
https://docs.google.com/spreadsheets/d/1_YH3KLAGSNzATkSUf9UEtFYhgA5s_R7IV-CFC_fye-s/edit

Columns: Timestamp, Download (Mbps), Upload (Mbps), Ping (ms), Server, Provider

## Site Data Export

After a successful run, the wrapper also updates:

- `{{HOME}}/kip-claw/src/lib/speedTests.json`

This file is the public data source used by kip-claw stats components.

## After Running

Report the results back to the user — download speed, upload speed, and ping.
Commit and push the JSON change in`{{HOME}}/kip-claw`.
If the user asks how it compares to recent tests, read the last few rows from the sheet using `gog --no-input -a "$GOG_ACCOUNT" sheets` and summarize the trend.

## Notes

- The test takes 20-30 seconds to complete
- Log: /var/log/kip-speedtest.log
- If the script fails, check that Tailscale is up and the NAS is reachable,
  then check /var/log/kip-speedtest.log for the specific error
