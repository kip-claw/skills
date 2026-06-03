#!/usr/bin/env python3
"""Append a Pi health reading to kip-claw's piHealth.json."""
import json
import os
import sys
from datetime import datetime

FIELDS = [
    "timestamp", "cpuTempC", "gpuTempC",
    "cpuLoad1m", "cpuLoad5m", "cpuLoad15m",
    "ramUsedMb", "ramTotalMb",
    "diskUsedGb", "diskTotalGb",
    "uptimeDays",
]


def main() -> int:
    if len(sys.argv) != len(FIELDS) + 2:
        print(
            f"Usage: pi-health-export-core.py <json_path> "
            + " ".join(f"<{f}>" for f in FIELDS),
            file=sys.stderr,
        )
        return 2

    json_path = sys.argv[1]
    timestamp = sys.argv[2]
    numeric_values = sys.argv[3:]

    row: dict = {"timestamp": timestamp}
    for field, raw in zip(FIELDS[1:], numeric_values):
        try:
            row[field] = float(raw) if raw != "" else None
        except ValueError:
            row[field] = None

    existing: list = []
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
        if not isinstance(existing, list):
            raise ValueError(f"Expected list in {json_path}")

    existing.append(row)
    existing.sort(key=lambda r: r.get("timestamp", ""))

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)

    return 0


sys.exit(main())
