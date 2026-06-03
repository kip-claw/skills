#!/usr/bin/env python3
"""Snapshot the humidor Google Sheet into a single JSON file for kip-claw."""
import json
import os
import subprocess
import sys


def gog_read(account: str, sheet_id: str, tab_range: str) -> list[list[str]]:
    """Read rows from a Google Sheet tab via gog CLI."""
    result = subprocess.run(
        [
            "gog", "--no-input", "-a", account,
            "sheets", "get", sheet_id, tab_range,
            "--json", "--results-only",
        ],
        capture_output=True, text=True, timeout=60,
        stdin=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        raise RuntimeError(f"gog read failed for {tab_range}: {result.stderr.strip()}")
    data = json.loads(result.stdout)
    return data if isinstance(data, list) else []


def rows_to_dicts(rows: list[list[str]], headers: list[str]) -> list[dict]:
    """Convert sheet rows (no header row) into a list of dicts."""
    out = []
    for row in rows:
        padded = row + [""] * (len(headers) - len(row))
        out.append({h: padded[i] for i, h in enumerate(headers)})
    return out


def main() -> int:
    if len(sys.argv) != 4:
        print(
            "Usage: humidor-data-export-core.py <json_path> <sheet_id> <gog_account>",
            file=sys.stderr,
        )
        return 2

    json_path, sheet_id, gog_account = sys.argv[1:4]

    # Read all three tabs — skip the header row (row 1) in each
    cigar_rows = gog_read(gog_account, sheet_id, "Cigars!A2:H")
    humidity_rows = gog_read(gog_account, sheet_id, "Humidity Readings!A2:E")
    boveda_rows = gog_read(gog_account, sheet_id, "Boveda Changes!A2:E")

    snapshot = {
        "cigars": rows_to_dicts(
            cigar_rows,
            ["dateAdded", "maker", "model", "wrapper", "origin", "size", "gauge", "notes"],
        ),
        "humidityReadings": rows_to_dicts(
            humidity_rows,
            ["date", "time", "rh", "temperatureF", "notes"],
        ),
        "bovedaChanges": rows_to_dicts(
            boveda_rows,
            ["dateChanged", "packType", "rh", "packCount", "notes"],
        ),
    }

    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)
        f.write("\n")

    print(
        f"Wrote {len(snapshot['cigars'])} cigars, "
        f"{len(snapshot['humidityReadings'])} readings, "
        f"{len(snapshot['bovedaChanges'])} boveda changes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
