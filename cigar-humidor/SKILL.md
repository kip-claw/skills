---
name: cigar-humidor
description: Log humidity readings, Boveda pack changes, and cigar additions to Ben's humidor Google Sheets. Use when asked to log humidity, add cigars, update humidor readings, or record Boveda pack changes.
metadata: {"openclaw": {"emoji": "🫘", "requires": {"bins": ["gog"]}}}
---

# Cigar Humidor (Google Sheets)

Manages Ben's cigar humidor tracking in a single Google Sheet with three tabs:
- **Cigar Log:** `https://docs.google.com/spreadsheets/d/1DqN2jOsFA7n6uwJnnDXV_dmlhIGCP39Pdxr8hZxwgK8/edit`

## Sheet Structure

### Tab 1: Cigars
Columns: `Date Added`, `Maker`, `Model`, `Wrapper`, `Origin`, `Size`, `Gauge`, `Notes`

- **Date Added**: Current date (YYYY-MM-DD)
- **Maker**: Cigar brand/maker (e.g., Martinez, Arturo Fuente, H. Upmann)
- **Model**: Specific cigar model/name (e.g., 654, Magnum Grand Reserva, The Banker)
- **Wrapper**: Wrapper leaf type (e.g., Maduro, Connecticut)
- **Origin**: Country of origin
- **Size**: Vitola/size (e.g., Robusto, Toro)
- **Gauge**: Ring gauge (e.g., 50, 52)
- **Notes**: Relevant notes about the cigar

### Tab 2: Humidity Readings
Columns: `Date`, `Time`, `RH%`, `Temperature (°F)`, `Notes`

- **Date**: Reading date (YYYY-MM-DD)
- **Time**: Optional time (HH:MM)
- **RH%**: Relative humidity percentage
- **Temperature (°F)**: Optional temperature
- **Notes**: Observations

### Tab 3: Boveda Changes
Columns: `Date Changed`, `Pack Type`, `RH%`, `Pack Count`, `Notes`

- **Date Changed**: Change date (YYYY-MM-DD)
- **Pack Type**: e.g., 65°, 69°, 72°
- **RH%**: Pack RH rating
- **Pack Count**: Number of packs
- **Notes**: Reason for change or observations

## Commands

### Log a Humidity Reading

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets append 1DqN2jOsFA7n6uwJnnDXV_dmlhIGCP39Pdxr8hZxwgK8 "Humidity Readings!A:E" \
  --values-json '[["2026-04-15","21:01","65","","Fresh reading"]]' \
  --insert INSERT_ROWS
```

### Log a Boveda Pack Change

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets append 1DqN2jOsFA7n6uwJnnDXV_dmlhIGCP39Pdxr8hZxwgK8 "Boveda Changes!A:E" \
  --values-json '[["2026-04-15","65°","1","","Monthly rotation"]]' \
  --insert INSERT_ROWS
```

### Add a Cigar

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets append 1DqN2jOsFA7n6uwJnnDXV_dmlhIGCP39Pdxr8hZxwgK8 "Cigars!A:H" \
  --values-json '[["2026-04-15","Montecristo","No. 2","Maduro","Cuba","Torpedo","52","Classic Cuban"]]'\
  --insert INSERT_ROWS
```

### Query Cigars

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets get 1DqN2jOsFA7n6uwJnnDXV_dmlhIGCP39Pdxr8hZxwgK8 "Cigars!A1:H20" --json
```

### Query Humidity Readings

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets get 1DqN2jOsFA7n6uwJnnDXV_dmlhIGCP39Pdxr8hZxwgK8 "Humidity Readings!A1:E10" --json
```

### Query Boveda Changes

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets get 1DqN2jOsFA7n6uwJnnDXV_dmlhIGCP39Pdxr8hZxwgK8 "Boveda Changes!A1:E10" --json
```

## Workflow Rules

- **Always confirm** before adding entries
- **Prompt for missing fields**: If Ben doesn't provide RH%, ask for it before adding humidity readings
- **Prompt for missing fields**: If Ben doesn't provide all cigar details, ask before adding
- **New entries go at the TOP** of each tab (row 2, right after the header)
- **Date format**: YYYY-MM-DD for all date fields
- **Time format**: HH:MM (optional)
- **Pack Type**: Use standard Boveda ratings (65°, 69°, 72°)

## Examples

### Log humidity reading (65% RH)

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets append 1DqN2jOsFA7n6uwJnnDXV_dmlhIGCP39Pdxr8hZxwgK8 "Humidity Readings!A:E" \
  --values-json '[["2026-04-15","21:01","65","","Fresh reading"]]' \
  --insert INSERT_ROWS
```

### Add cigar to log

```bash
gog --no-input -a "$GOG_ACCOUNT" sheets append 1DqN2jOsFA7n6uwJnnDXV_dmlhIGCP39Pdxr8hZxwgK8 "Cigars!A:H" \
  --values-json '[["2026-04-15","Montecristo","No. 2","Maduro","Cuba","Torpedo","52","Classic Cuban"]]'\
  --insert INSERT_ROWS
```

## Notes

- Sheet ID: `1DqN2jOsFA7n6uwJnnDXV_dmlhIGCP39Pdxr8hZxwgK8`
- Tabs: `Cigars`, `Humidity Readings`, `Boveda Changes`
- Requires `gog` with Sheets API access (service-level account context is preconfigured)
- Old Obsidian files archived: `{{HOME}}/obsidian-vault/Projects/Cigar Humidor Humidity Log.md` and `{{HOME}}/obsidian-vault/Projects/Cigar Log.md`
- Separate Humidity Log sheet (`1Wf5klf_gH85ciBEQVtAvIbtVqNEzFY6Rl8G_RwfjStg`) can be deleted or archived
