---
name: "cigar-humidor"
description: "Track cigar inventory and analyze hourly humidor readings from Home Assistant."
metadata: {"openclaw": {"emoji": "🫘"}}
---

# Cigar Humidor (Google Sheets + Home Assistant)

Manages Ben's cigar inventory and Boveda records in the **Cigar Log** Google
spreadsheet. Find it by title with the Google Workspace MCP rather than
hard-coding its ID.

## Sheet Structure

### Tab 1: Cigars
Columns: `Date Added`, `Maker`, `Model`, `Wrapper`, `Origin`, `Size`, `Gauge`, `Notes`

### Legacy tab: Humidity Readings
The `Humidity Readings` tab in **Cigar Log** is a historical manual log. Keep
its existing rows, but do not append new readings there and do not use it as the
source for the website chart.

### Automatic humidity source: Humidor Sensor Log
Home Assistant appends hourly Zooz ZSE44 readings to the **Humidor Sensor Log**
spreadsheet, tab **Humidor Readings**. Find it by title with the Google
Workspace MCP. Columns are `Timestamp`, `Humidity (%)`, `Temperature (°F)`, and
`Sensor`. This is the canonical source for current readings, analysis, and the
kip.computer chart.

### Tab 3: Boveda Changes
Columns: `Date Changed`, `Pack Type`, `RH%`, `Pack Count`, `Notes`

### Tab 4: Smoked Cigars
Columns: `Make`, `Model`, `Date`, `Notes`

## Google Workspace MCP

Use the Google Workspace MCP and the connected Google account. Resolve workbook
IDs by exact title with `list_spreadsheets`; do not hard-code IDs. For
interactive work, use `read_sheet_values` and `modify_sheet_values`, and read
back each changed row before confirming. The unattended website exporter uses
`gog` with IDs stored in the local OpenClaw environment file; never expose
those IDs in public skill source.

## Humidity readings

- For current conditions or analysis, read **Humidor Sensor Log → Humidor
  Readings**. Each row has a local timestamp, RH, temperature, and sensor name.
- The workbook grows by one row per hour. For long histories, read bounded row
  ranges in chunks of at most 1,000 rows until no more rows are returned.
- Do not write readings to the retired manual `Cigar Log → Humidity Readings`
  tab. Preserve its historical entries unchanged.
- The website exporter uses the automatic sensor workbook for
  `humidityReadings`; the manual tab is no longer included in the chart feed.

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

- Cigar workbook tabs: `Cigars`, legacy `Humidity Readings`, `Boveda Changes`,
  and `Smoked Cigars`.
- Sensor workbook: `Humidor Sensor Log` → `Humidor Readings`.
- Requires Google Workspace MCP Sheets access.
