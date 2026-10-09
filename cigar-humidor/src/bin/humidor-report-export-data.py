#!/usr/bin/env python3
"""Snapshot the humidor Google Sheet into a single JSON file for kip-claw."""
import json
import os
import re
import subprocess
import sys
from datetime import datetime

LOOSE_ISO_HOUR = re.compile(r"^(\d{4}-\d{2}-\d{2}[ T])(\d)(?=:)")


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


def sensor_rows_to_dicts(rows: list[list[str]]) -> list[dict]:
    """Convert Home Assistant sensor rows into the site's humidity format."""
    readings = []
    for row in rows:
        padded = row + [""] * (4 - len(row))
        timestamp, rh, temperature_f, _sensor = (str(value).strip() for value in padded[:4])
        if not timestamp or not rh:
            continue

        # Some source rows use an unpadded hour, e.g. "2026-10-08 0:00:00".
        # Normalize that one looser ISO-8601 variant before strict parsing.
        normalized_timestamp = LOOSE_ISO_HOUR.sub(r"\g<1>0\2", timestamp, count=1)
        parsed = datetime.fromisoformat(normalized_timestamp.replace("T", " ", 1))
        readings.append(
            {
                "date": parsed.date().isoformat(),
                "time": parsed.strftime("%H:%M:%S"),
                "rh": rh,
                "temperatureF": temperature_f,
                "notes": "",
            }
        )
    return readings


def main() -> int:
    if len(sys.argv) != 5:
        print(
            "Usage: humidor-data-export-core.py <json_path> <cigar_sheet_id> <sensor_sheet_id> <gog_account>",
            file=sys.stderr,
        )
        return 2

    json_path, cigar_sheet_id, sensor_sheet_id, gog_account = sys.argv[1:5]

    # Keep inventory and Boveda data in the original workbook. Humidity now
    # comes only from the Home Assistant sensor workbook.
    cigar_rows = gog_read(gog_account, cigar_sheet_id, "Cigars!A2:H")
    sensor_rows = gog_read(gog_account, sensor_sheet_id, "Humidor Readings!A2:D")
    boveda_rows = gog_read(gog_account, cigar_sheet_id, "Boveda Changes!A2:E")

    snapshot = {
        "cigars": rows_to_dicts(
            cigar_rows,
            ["dateAdded", "maker", "model", "wrapper", "origin", "size", "gauge", "notes"],
        ),
        "humidityReadings": sensor_rows_to_dicts(sensor_rows),
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
