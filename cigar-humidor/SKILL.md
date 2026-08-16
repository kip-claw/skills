---
name: "cigar-humidor"
description: "Add a current-aging summary workflow for every logged cigar."
tag: Lists
metadata: {"openclaw": {"emoji": "🫘", "requires": {"bins": ["gog"]}}}
---

# Cigar Humidor (Google Sheets)

Manages Ben's cigar humidor tracking in a single Google Sheet with four tabs:
- **Cigar Log:** `https://docs.google.com/spreadsheets/d/1DqN2jOsFA7n6uwJnnDXV_dmlhIGCP39Pdxr8hZxwgK8/edit`

## Sheet Structure

### Tab 1: Cigars
Columns: `Date Added`, `Maker`, `Model`, `Wrapper`, `Origin`, `Size`, `Gauge`, `Notes`

### Tab 2: Humidity Readings
Columns: `Date`, `Time`, `RH%`, `Temperature (°F)`, `Notes`

### Tab 3: Boveda Changes
Columns: `Date Changed`, `Pack Type`, `RH%`, `Pack Count`, `Notes`

### Tab 4: Smoked Cigars
Columns: `Make`, `Model`, `Date`, `Notes`

## Commands

### Query cigars

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets get 1DqN2jOsFA7n6uwJnnDXV_dmlhIGCP39Pdxr8hZxwgK8 "Cigars!A1:H1000" --json
```

### Add a cigar

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets append 1DqN2jOsFA7n6uwJnnDXV_dmlhIGCP39Pdxr8hZxwgK8 "Cigars!A:H" \
  --values-json '[["2026-04-15","Montecristo","No. 2","Maduro","Cuba","Torpedo","52","Classic Cuban"]]' \
  --insert INSERT_ROWS
```

## Aging Summary

When Ben asks how long cigars have been aging:

1. Query `Cigars!A1:H1000`.
2. Treat each `Date Added` as the aging start date; use the current date in America/New_York as the end date.
3. Calculate elapsed full calendar days for every logged cigar.
4. Return every cigar, oldest first, as concise Telegram-friendly bullets: `Maker Model — N days`.
5. State that the calculation is based on the recorded date added. Do not modify the sheet.

## Workflow Rules

- Always confirm before adding or changing entries.
- Prompt for missing details before adding a cigar.
- New entries go at the top of each tab, in row 2 after the header.
- Use `YYYY-MM-DD` for all dates.
- Keep Telegram replies concise; do not use tables.

## Notes

- Sheet ID: `1DqN2jOsFA7n6uwJnnDXV_dmlhIGCP39Pdxr8hZxwgK8`
- Tabs: `Cigars`, `Humidity Readings`, `Boveda Changes`, `Smoked Cigars`
- Requires `gog` with Sheets API access.
