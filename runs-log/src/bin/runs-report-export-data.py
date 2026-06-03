#!/usr/bin/env python3
"""Snapshot the runs log Google Sheet into a JSON file for kip-claw."""
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
            "Usage: runs-log-export-core.py <json_path> <sheet_id> <gog_account>",
            file=sys.stderr,
        )
        return 2

    json_path, sheet_id, gog_account = sys.argv[1:4]

    run_rows = gog_read(gog_account, sheet_id, "Sheet1!A2:D")

    runs = rows_to_dicts(
        run_rows,
        ["date", "distance", "route", "reflections"],
    )

    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(runs, f, indent=2)
        f.write("\n")

    print(f"Wrote {len(runs)} runs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
