---
name: nyc-list
title: NYC List
description: Tracks the New York City places Ben has visited.
tag: Lists
metadata: {"openclaw": {"emoji": "🗽", "requires": {"bins": ["gog"]}}}
---

# NYC List Skill

Manages Ben's NYC list Google Sheet: `https://docs.google.com/spreadsheets/d/1GeVkWdyqKM7P8A0MGwWns3fOketRR5ThnubSEaIKJEQ/edit`

## Sheet Structure

### List tab
Columns: `name`, `address`, `is_decent`, `is_recommended`, `is_elite`, `is_closed`, `notes`

- **name**: Place name (e.g., `2A`, `2nd Ave. Deli`)
- **address**: Full address (e.g., `25 Avenue A, New York, NY 10009`)
- **is_decent**: `Y` or `N` (green background if Y, purple if N)
- **is_recommended**: `Y` or `N`
- **is_elite**: `Y` or `N`
- **is_closed**: `Y` or `N`
- **notes**: Brief review or comment (1-2 sentences, candid and practical)

## Sorting

**The List tab is sorted alphabetically by `name` (ascending).**

When adding new entries:
1. Add the new place to the sheet
2. Sort the entire list alphabetically by the `name` column with `{{HOME}}/bin/nyc-list-sort.sh`
3. The sheet should remain in alphabetical order at all times

## Commands

### Add a new place

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets append 1GeVkWdyqKM7P8A0MGwWns3fOketRR5ThnubSEaIKJEQ "List!A:G" \
  --values-json '[["2nd Ave. Deli","162 E 33rd St, New York, NY 10016","Y","Y","N","N","Old school Jewish deli with the classic sandwiches and sides"]]' \
  --insert INSERT_ROWS
```

### Query the list

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets get 1GeVkWdyqKM7P8A0MGwWns3fOketRR5ThnubSEaIKJEQ "List!A1:G20" --json
```

### Search by name or address

Use `gog --no-input -a "$GOG_ACCOUNT" sheets get` with a larger range, then filter results in your script.

### Update a place's status

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets update 1GeVkWdyqKM7P8A0MGwWns3fOketRR5ThnubSEaIKJEQ "List!C10" \
  --values-json '[["Y"]]' \
  --input USER_ENTERED
```

### Sort the list

```bash
{{HOME}}/bin/nyc-list-sort.sh
```

## Workflow Rules
- **If address is missing**: look up the address on the web (e.g., via a quick search) before adding the entry

- **Always confirm** before adding or updating places
- **Show the full draft entry** in the confirmation message so Ben can approve the exact row that will be written
- **Ask for confirmation immediately after drafting**; do not stop at analysis or leave the request hanging without a direct approval prompt
- **If waiting on approval**: say plainly that no change has been made yet and that the task is paused pending Ben's confirmation
- **Always report completion** after adding or updating a row so Ben knows the change was actually made
- **Alphabetical order**: After adding, sort the list by `name` ascending
- **is_decent**: Ask Ben for Y/N; this affects background color (Y=green, N=purple)
- **is_recommended**: Y/N flag for places Ben recommends
- **is_elite**: Y/N flag for special/elite tier places
- **is_closed**: Mark Y if the place has closed
- **notes**: Keep brief and candid, like existing entries (1-2 sentences)
- **Address format**: Use full Google Maps-style addresses

## Examples

### Confirmation message before add

Use a direct confirmation prompt with the exact row contents:

```text
Confirm this NYC list entry and I'll add it:
- name: Joe's Pizza
- address: 150 E 14th St, New York, NY 10003
- is_decent: Y
- is_recommended: Y
- is_elite: N
- is_closed: N
- notes: My neighborhood outpost of the famous pizza purveyor. Decent and reliably recommended for a slice nearby.
```

### Add a new place (recommended, decent)

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets append 1GeVkWdyqKM7P8A0MGwWns3fOketRR5ThnubSEaIKJEQ "List!A:G" \
  --values-json '[["5ive Spice","363 3rd Ave, New York, NY 10016","Y","Y","N","N","Great vietnamese food, including pho"]]' \
  --insert INSERT_ROWS
```

### Read the list

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets get 1GeVkWdyqKM7P8A0MGwWns3fOketRR5ThnubSEaIKJEQ "List!A1:G30" --json
```

## Notes

- Sheet ID: `1GeVkWdyqKM7P8A0MGwWns3fOketRR5ThnubSEaIKJEQ`
- Title: "Ben's NYC list"
- Timezone: `America/New_York`
- Requires `gog` with Sheets API access (service-level account context is preconfigured)
- The sheet has conditional formatting: Y = green, N = purple on is_decent column
- The sheet has a basic filter applied and is sorted ascending by name
