---
name: "cigar-humidor"
description: "Add a current-aging summary workflow for every logged cigar."
metadata: {"openclaw": {"emoji": "🫘"}}
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

## Google Workspace MCP

Use the Google Workspace MCP for spreadsheet `1DqN2jOsFA7n6uwJnnDXV_dmlhIGCP39Pdxr8hZxwgK8`. Always pass `user_google_email: "kip@palewi.re"`; do not use `gog`. Read with `read_sheet_values`, make row changes with `modify_sheet_values`, and read back each changed row before confirming.

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
- Requires Google Workspace MCP Sheets access.
