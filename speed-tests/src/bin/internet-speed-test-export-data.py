#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime


def parse_timestamp(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


def normalize_row(timestamp: str, download: str, upload: str, ping: str, server: str, provider: str):
    return {
        "timestamp": timestamp,
        "downloadMbps": float(download),
        "uploadMbps": float(upload),
        "pingMs": float(ping),
        "server": server,
        "provider": provider,
    }


def row_key(row: dict) -> str:
    return "|".join(
        [
            str(row.get("timestamp", "")),
            str(row.get("downloadMbps", "")),
            str(row.get("uploadMbps", "")),
            str(row.get("pingMs", "")),
            str(row.get("server", "")),
            str(row.get("provider", "")),
        ]
    )


def main() -> int:
    if len(sys.argv) != 8:
        print(
            "Usage: network-speedtest-export-core.py <json_path> <timestamp> <download> <upload> <ping> <server> <provider>",
            file=sys.stderr,
        )
        return 2

    json_path, timestamp, download, upload, ping, server, provider = sys.argv[1:8]
    new_row = normalize_row(timestamp, download, upload, ping, server, provider)

    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
        if not isinstance(existing, list):
            raise ValueError(f"Expected list in {json_path}")
    else:
        existing = []

    keyed = {row_key(row): row for row in existing if isinstance(row, dict)}
    keyed[row_key(new_row)] = new_row

    rows = list(keyed.values())
    rows.sort(key=lambda row: parse_timestamp(row["timestamp"]))

    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)
        f.write("\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
