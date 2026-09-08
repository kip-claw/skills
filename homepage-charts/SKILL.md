---
name: homepage-charts
description: Logs the graphics that reach the Reuters homepage to Ben's spreadsheet.
metadata: {"openclaw": {"emoji": "📊"}}
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

## Google Workspace MCP

Use the Google Workspace MCP for spreadsheet `1ZfPHAdOJiK8vsQXpdslHXERRHDukZA8WXTuSY9JMbms`. Always pass `user_google_email: "kip@palewi.re"`; do not use `gog`. Read `List` with `read_sheet_values`, check for a same-date duplicate, append with `modify_sheet_values`, and read back the new row.

## Workflow Rules
- When asking for approval, show the data row that will be inserted (date, chart, notes), not a tool call.

- **Always confirm** before adding entries
- **Date**: Use today's date (YYYY-MM-DD) unless Ben specifies otherwise
- **Chart**: Use the brief description Ben provides
- **Notes**: Leave blank (`""`) unless Ben explicitly provides a note
- **No duplicates**: Don't create duplicate entries for the same chart on the same date

## Notes

- Sheet ID: `1ZfPHAdOJiK8vsQXpdslHXERRHDukZA8WXTuSY9JMbms`
- Requires Google Workspace MCP Sheets access.
