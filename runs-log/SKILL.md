---
name: runs-log
description: Records the date, distance, route, and reflections from Ben's runs.
metadata: {"openclaw": {"emoji": "🏃"}}
---

# Runs Log (Google Sheets)

Manages Ben's runs log in Google Sheets:
- **Runs Log:** `https://docs.google.com/spreadsheets/d/1ybViNc3uJp9Be7Os5Cryu6E83VTxB0ZqWPRYYiQAMfA/edit`

## Sheet Structure

### Runs tab
Columns: `Date`, `Distance`, `Route`, `Reflections`

- **Date**: Run date (YYYY-MM-DD)
- **Distance**: Distance with unit (e.g., `7 miles`, `15 miles`, `10 km`)
- **Route**: Route description (e.g., `Central Park loop`, `Queensborough Bridge and back`)
- **Reflections**: Personal notes about the run (feel, conditions, observations)

## Google Workspace MCP

Use the Google Workspace MCP for spreadsheet `1ybViNc3uJp9Be7Os5Cryu6E83VTxB0ZqWPRYYiQAMfA`. Always pass `user_google_email: "kip@palewi.re"`; do not use `gog`. Read `Sheet1` to check duplicates, append with `modify_sheet_values`, then read back the written row.

## Workflow Rules

- **Always confirm** before adding entries
- **Date format**: YYYY-MM-DD
- **Distance**: Include unit (miles, km, etc.)
- **Route**: Keep concise but descriptive
- **Reflections**: Personal, terse notes about the run
- **No duplicates**: Don't create duplicate entries for the same run

## Notes

- Sheet ID: `1ybViNc3uJp9Be7Os5Cryu6E83VTxB0ZqWPRYYiQAMfA`
- Requires Google Workspace MCP Sheets access.
- Old Obsidian file archived: `{{HOME}}/obsidian-vault/Projects/Runs Log.md`
