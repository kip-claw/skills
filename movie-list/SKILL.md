---
name: movie-list
description: Tracks the films Ben has watched and the ones he wants to see.
metadata: {"openclaw": {"emoji": "🎬"}}
---

# Movie List Skill

Manages Ben's movie list Google Sheet: `https://docs.google.com/spreadsheets/d/1AmRHTmZ8i4NPGEDeLoTkanp3Zw3QmhW8lI6W9fFLJcg/edit`

## Sheet Structure

### Watched tab
Columns: `Title`, `Released`, `Viewing`, `Venue`, `Rating`, `Notes`

- **Title**: Movie title
- **Released**: Year the movie was released (e.g., `2025`, `1928`)
- **Viewing**: Date watched (e.g., `3/14/2026`, `2/14/2026`)
- **Venue**: Where it was watched (e.g., `Streaming`, `Film Forum`, `Paris`, theater name)
- **Rating**: 👍 (liked) or 👎 (didn't like)
- **Notes**: Brief review or comment

### Wishlist tab
Columns: Likely `Title` and possibly `Released` or other metadata (similar to reading list wishlist)

- **Title**: Movie title
- Additional columns may exist but are not required

## Google Workspace MCP

Use the Google Workspace MCP for spreadsheet `1AmRHTmZ8i4NPGEDeLoTkanp3Zw3QmhW8lI6W9fFLJcg`. Always pass `user_google_email: "kip@palewi.re"`; do not use `gog`. Read `Watched` or `Wishlist` with `read_sheet_values`, append or update with `modify_sheet_values`, and read back every changed row. Search a sufficiently large range and filter the returned values by title or year.

## Workflow Rules

- **Always confirm** before adding or moving movies
- **Viewing date**: Use the actual date watched (MM/DD/YYYY format)
- **Venue**: Ask if not specified; common values: `Streaming`, `Film Forum`, theater names
- **Rating**: Ask Ben for 👍 or 👎; don't assume
- **Notes**: Keep brief, like the existing entries (1-2 sentences max)
- **Wishlist → Watched**: When Ben watches a wishlist movie, move it (don't duplicate)

## Notes

- Sheet ID: `1AmRHTmZ8i4NPGEDeLoTkanp3Zw3QmhW8lI6W9fFLJcg`
- Title: "Ben's movie list"
- Timezone: `America/New_York`
- Requires Google Workspace MCP Sheets access.
