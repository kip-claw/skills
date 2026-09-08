---
name: reading-list
description: Tracks the books Ben has finished and the ones he wants to read.
metadata: {"openclaw": {"emoji": "📚"}}
---

# Reading List Skill

Manages Ben's reading list Google Sheet: `https://docs.google.com/spreadsheets/d/1iLziNbQPM_wP162YA8FcqhHhXCkFcCvhpTNa67WGywI/edit`

## Sheet Structure

### Finished tab
Columns: `Title`, `Author`, `Year Read`, `Medium`, `Year Published`, `Read Order`, `Date Finished`, `Book ID`

- **Title**: Book title
- **Author**: Author name(s)
- **Year Read**: Year completed (e.g., `2025`, `2026`)
- **Medium**: One of: `Audiobook`, `E-Book`, `Print book`
- **Year Published**: Year the book was first published (e.g., `1952`, `2003`). Fill this in for every new book added.
- **Read Order**: Sequential lifetime reading order. The earliest finished book is `1`, and each newly finished book gets the next integer.
- **Date Finished**: Date the finished book is logged, in `YYYY-MM-DD` format using `America/New_York`.
- **Book ID**: Stable join key for book metadata, formatted like `book-0104`.

### Book Metadata tab
Columns: `Book ID`, `Title`, `Author`, `ISBN 13`, `ISBN 10`, `Open Library ID`, `Google Books ID`, `Publisher`, `Published Date`, `Page Count`, `Language`, `Subjects`, `Description`, `Cover URL`, `Metadata Source`, `Metadata Checked`, `Metadata Confidence`, `Metadata Notes`

- **Book ID**: Join key back to `Finished`
- **Metadata Source**: Which lookup source supplied the data, typically `Open Library`, `Google Books`, or both
- **Metadata Checked**: Date metadata was last refreshed
- **Metadata Confidence**: `High`, `Medium`, `Low`, or `Unmatched`
- **Metadata Notes**: Short note about match quality or ambiguity

### Wishlist tab
Columns: `Title`, `Author`

- **Title**: Book title
- **Author**: Author name(s)
- Additional columns may exist but are not required

### Medium by year tab
Pivot table summary. Do not edit directly — it auto-updates from Finished.

## Google Workspace MCP

Use the Google Workspace MCP for spreadsheet `1iLziNbQPM_wP162YA8FcqhHhXCkFcCvhpTNa67WGywI`. Always pass `user_google_email: "kip@palewi.re"`; do not use `gog`. Read target ranges with `read_sheet_values`, modify rows with `modify_sheet_values`, and read back every changed row. To create a finished-book row, read `Finished!F2:F500`, calculate the next numeric read order, and derive `Book ID` as `book-%04d`.

### Move from Wishlist to Finished

1. Read the wishlist entry
2. Read `Finished!F2:F`, compute the next `Read Order`, build `Book ID`, set `Date Finished` to today's `America/New_York` date, and append to Finished with Year Read, Medium, Year Published, Read Order, Date Finished, and Book ID
3. Look up metadata by ISBN first when available, otherwise by title and author using Open Library and Google Books
4. Append or update the `Book Metadata` row for that `Book ID`, recording `Metadata Source`, `Metadata Checked`, `Metadata Confidence`, and `Metadata Notes`
5. Optionally delete from Wishlist (requires manual confirmation)

### Query and search

Read the relevant `Finished`, `Wishlist`, or `Book Metadata` range with `read_sheet_values`; for author/title searches, read a sufficiently large range and filter returned values.

## Workflow Rules

- **Always confirm** before adding or moving books
- **Year Read**: Use the current year unless Ben specifies otherwise
- **Medium**: Ask if not specified; default to `Audiobook` if Ben mentions listening
- **Year Published**: Fill this in for every new book. Ask Ben if unknown, or look it up.
- **Read Order**: Always calculate `MAX(Read Order)+1` before appending to Finished.
- **Date Finished**: Always fill with `TZ=America/New_York date +%F` when appending to Finished unless Ben specifies a different finished/logged date.
- **Book ID**: Always derive from `Read Order` using `book-%04d`.
- **Metadata lookup**: Prefer ISBN lookup when available. Otherwise search by title and author.
- **Metadata confidence**: Record `High`, `Medium`, `Low`, or `Unmatched` instead of silently writing uncertain metadata.
- **Audiobook details**: Preserve narrator, publisher, release date, duration, or other edition-specific audiobook details in `Metadata Notes` when Ben provides them or they are found during lookup.
- **Wishlist → Finished**: When Ben finishes a wishlist book, move it (don't duplicate)
- **Never edit Medium by year** — it's a pivot summary

## Notes

- Sheet ID: `1iLziNbQPM_wP162YA8FcqhHhXCkFcCvhpTNa67WGywI`
- Title: "Ben's book list"
- Timezone: `America/New_York`
- Requires Google Workspace MCP Sheets access.
