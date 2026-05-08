---
name: reading-list
description: Maintain Ben's reading list Google Sheet. Add books to Finished or Wishlist, update reading status, and query the sheet.
metadata: {"openclaw": {"emoji": "📚", "requires": {"bins": ["gog"]}}}
---

# Reading List Skill

Manages Ben's reading list Google Sheet: `https://docs.google.com/spreadsheets/d/1iLziNbQPM_wP162YA8FcqhHhXCkFcCvhpTNa67WGywI/edit`

## Sheet Structure

### Finished tab
Columns: `Title`, `Author`, `Year Read`, `Medium`, `Year Published`

- **Title**: Book title
- **Author**: Author name(s)
- **Year Read**: Year completed (e.g., `2025`, `2026`)
- **Medium**: One of: `Audiobook`, `E-Book`, `Print book`
- **Year Published**: Year the book was first published (e.g., `1952`, `2003`). Fill this in for every new book added.

### Wishlist tab
Columns: `Title`, `Author`

- **Title**: Book title
- **Author**: Author name(s)
- Additional columns may exist but are not required

### Medium by year tab
Pivot table summary. Do not edit directly — it auto-updates from Finished.

## Commands

### Add a finished book

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets append 1iLziNbQPM_wP162YA8FcqhHhXCkFcCvhpTNa67WGywI "Finished!A:E" \
  --values-json '[["Title","Author","2025","Audiobook","2003"]]' \
  --insert INSERT_ROWS
```

### Add to wishlist

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets append 1iLziNbQPM_wP162YA8FcqhHhXCkFcCvhpTNa67WGywI "Wishlist!A:B" \
  --values-json '[["Title","Author"]]' \
  --insert INSERT_ROWS
```

### Move from Wishlist to Finished

1. Read the wishlist entry
2. Append to Finished with Year Read, Medium, and Year Published
3. Optionally delete from Wishlist (requires manual confirmation)

### Query Finished books

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets get 1iLziNbQPM_wP162YA8FcqhHhXCkFcCvhpTNa67WGywI "Finished!A1:E50" --json
```

### Query Wishlist

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets get 1iLziNbQPM_wP162YA8FcqhHhXCkFcCvhpTNa67WGywI "Wishlist!A1:B50" --json
```

### Search by author or title

Use `gog --no-input -a "$GOG_ACCOUNT" sheets get` with a larger range, then filter results in your script.

## Workflow Rules

- **Always confirm** before adding or moving books
- **Year Read**: Use the current year unless Ben specifies otherwise
- **Medium**: Ask if not specified; default to `Audiobook` if Ben mentions listening
- **Year Published**: Fill this in for every new book. Ask Ben if unknown, or look it up.
- **Wishlist → Finished**: When Ben finishes a wishlist book, move it (don't duplicate)
- **Never edit Medium by year** — it's a pivot summary

## Examples

### Add finished book (audiobook, 2026)

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets append 1iLziNbQPM_wP162YA8FcqhHhXCkFcCvhpTNa67WGywI "Finished!A:E" \
  --values-json '[["The Old Man and the Sea","Ernest Hemingway","2026","Audiobook","1952"]]' \
  --insert INSERT_ROWS
```

### Add to wishlist

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets append 1iLziNbQPM_wP162YA8FcqhHhXCkFcCvhpTNa67WGywI "Wishlist!A:B" \
  --values-json '[["Unequal","Eugenia Chang"]]' \
  --insert INSERT_ROWS
```

### Read recent finished books

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets get 1iLziNbQPM_wP162YA8FcqhHhXCkFcCvhpTNa67WGywI "Finished!A1:E20" --json
```

## Notes

- Sheet ID: `1iLziNbQPM_wP162YA8FcqhHhXCkFcCvhpTNa67WGywI`
- Title: "Ben's book list"
- Timezone: `America/New_York`
- Requires `gog` with Sheets API access (service-level account context is preconfigured)
