---
name: movie-list
description: Tracks the films Ben has watched and the ones he wants to see.
tag: Lists
metadata: {"openclaw": {"emoji": "🎬", "requires": {"bins": ["gog"]}}}
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

## Commands

### Add a watched movie

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets append 1AmRHTmZ8i4NPGEDeLoTkanp3Zw3QmhW8lI6W9fFLJcg "Watched!A:F" \
  --values-json '[["Blue Moon","2025","3/14/2026","Streaming","👍","Ethan Hawke talker set at Sardi\'s"]]' \
  --insert INSERT_ROWS
```

### Add to wishlist

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets append 1AmRHTmZ8i4NPGEDeLoTkanp3Zw3QmhW8lI6W9fFLJcg "Wishlist!A:B" \
  --values-json '[["Title","Released"]]' \
  --insert INSERT_ROWS
```

### Query Watched movies

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets get 1AmRHTmZ8i4NPGEDeLoTkanp3Zw3QmhW8lI6W9fFLJcg "Watched!A1:F20" --json
```

### Query Wishlist

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets get 1AmRHTmZ8i4NPGEDeLoTkanp3Zw3QmhW8lI6W9fFLJcg "Wishlist!A1:B20" --json
```

### Search by title or year

Use `gog --no-input -a "$GOG_ACCOUNT" sheets get` with a larger range, then filter results in your script.

## Workflow Rules

- **Always confirm** before adding or moving movies
- **Viewing date**: Use the actual date watched (MM/DD/YYYY format)
- **Venue**: Ask if not specified; common values: `Streaming`, `Film Forum`, theater names
- **Rating**: Ask Ben for 👍 or 👎; don't assume
- **Notes**: Keep brief, like the existing entries (1-2 sentences max)
- **Wishlist → Watched**: When Ben watches a wishlist movie, move it (don't duplicate)

## Examples

### Add watched movie (2025, streaming, liked)

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets append 1AmRHTmZ8i4NPGEDeLoTkanp3Zw3QmhW8lI6W9fFLJcg "Watched!A:F" \
  --values-json '[["Blue Moon","2025","3/14/2026","Streaming","👍","Ethan Hawke talker set at Sardi\'s"]]' \
  --insert INSERT_ROWS
```

### Add to wishlist

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets append 1AmRHTmZ8i4NPGEDeLoTkanp3Zw3QmhW8lI6W9fFLJcg "Wishlist!A:B" \
  --values-json '[["Dune 3","2026"]]' \
  --insert INSERT_ROWS
```

### Read recent watched movies

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets get 1AmRHTmZ8i4NPGEDeLoTkanp3Zw3QmhW8lI6W9fFLJcg "Watched!A1:F10" --json
```

## Notes

- Sheet ID: `1AmRHTmZ8i4NPGEDeLoTkanp3Zw3QmhW8lI6W9fFLJcg`
- Title: "Ben's movie list"
- Timezone: `America/New_York`
- Requires `gog` with Sheets API access (service-level account context is preconfigured)
