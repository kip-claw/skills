---
name: homepage-charts
description: Logs the graphics that reach the Reuters homepage to Ben's spreadsheet.
tag: Work
metadata: {"openclaw": {"emoji": "📊", "requires": {"bins": ["gog"]}}}
---

# Homepage Charts (Google Sheets)

Tracks every time a graphic made by Ben's Reuters team is featured on the reuters.com homepage:
- **Homepage Charts:** `https://docs.google.com/spreadsheets/d/1ZfPHAdOJiK8vsQXpdslHXERRHDukZA8WXTuSY9JMbms/edit`

## Sheet Structure

### List tab
Columns: `Date`, `Chart`, `Notes`

- **Date**: Date the chart appeared on the homepage (YYYY-MM-DD). Use today's date if not specified.
- **Chart**: Brief description of the chart (e.g., `Oil prices this year`, `US Consumer Price Index month to month`). Capitalize the first letter of the chart title.
- **Notes**: Optional additional context or notes (usually left blank)

## Commands

### Add a Homepage Chart Entry

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets append 1ZfPHAdOJiK8vsQXpdslHXERRHDukZA8WXTuSY9JMbms 'List!A:C' \
  --values-json '[["2026-04-17","Oil prices this year",""]]' \
  --insert INSERT_ROWS
```

### Query Recent Entries

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets get 1ZfPHAdOJiK8vsQXpdslHXERRHDukZA8WXTuSY9JMbms 'List!A1:C20' --json
```

## Workflow Rules
- When asking for approval, show the data row that will be inserted (date, chart, notes) rather than the full `gog` command.

- **Always confirm** before adding entries
- **Date**: Use today's date (YYYY-MM-DD) unless Ben specifies otherwise
- **Chart**: Use the brief description Ben provides
- **Notes**: Leave blank (`""`) unless Ben explicitly provides a note
- **No duplicates**: Don't create duplicate entries for the same chart on the same date

## Examples

### Add a homepage chart (no notes)

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets append 1ZfPHAdOJiK8vsQXpdslHXERRHDukZA8WXTuSY9JMbms 'List!A:C' \
  --values-json '[["2026-04-17","Strait of Hormuz transits",""]]' \
  --insert INSERT_ROWS
```

### Add a homepage chart (with notes)

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets append 1ZfPHAdOJiK8vsQXpdslHXERRHDukZA8WXTuSY9JMbms 'List!A:C' \
  --values-json '[["2026-04-17","Retail US gas prices","First LSEG shipping data chart"]]' \
  --insert INSERT_ROWS
```

### Read recent entries

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets get 1ZfPHAdOJiK8vsQXpdslHXERRHDukZA8WXTuSY9JMbms 'List!A1:C10' --json
```

## Notes

- Sheet ID: `1ZfPHAdOJiK8vsQXpdslHXERRHDukZA8WXTuSY9JMbms`
- Requires `gog` with Sheets API access (service-level account context is preconfigured)
