---
name: runs-log
description: Update Ben's runs log in Google Sheets. Use when asked to add a run or log date, distance, route description, and reflections for a workout.
metadata: {"openclaw": {"emoji": "🏃", "requires": {"bins": ["gog"]}}}
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

## Commands

### Add a Run

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets append 1ybViNc3uJp9Be7Os5Cryu6E83VTxB0ZqWPRYYiQAMfA "Sheet1!A:D" \
  --values-json '[["2026-04-15","5 mi","Central Park loop","Felt strong, saw the reservoir"]]' \
  --insert INSERT_ROWS
```

### Query Runs

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets get 1ybViNc3uJp9Be7Os5Cryu6E83VTxB0ZqWPRYYiQAMfA "Sheet1!A1:D20" --json
```

## Workflow Rules

- **Always confirm** before adding entries
- **Date format**: YYYY-MM-DD
- **Distance**: Include unit (miles, km, etc.)
- **Route**: Keep concise but descriptive
- **Reflections**: Personal, terse notes about the run
- **No duplicates**: Don't create duplicate entries for the same run

## Examples

### Add a run (5 miles, Central Park)

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets append 1ybViNc3uJp9Be7Os5Cryu6E83VTxB0ZqWPRYYiQAMfA "Sheet1!A:D" \
  --values-json '[["2026-04-15","5 mi","Central Park loop","Felt strong, saw the reservoir"]]' \
  --insert INSERT_ROWS
```

### Read recent runs

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets get 1ybViNc3uJp9Be7Os5Cryu6E83VTxB0ZqWPRYYiQAMfA "Sheet1!A1:D10" --json
```

## Notes

- Sheet ID: `1ybViNc3uJp9Be7Os5Cryu6E83VTxB0ZqWPRYYiQAMfA`
- Requires `gog` with Sheets API access (service-level account context is preconfigured)
- Old Obsidian file archived: `{{HOME}}/obsidian-vault/Projects/Runs Log.md`
