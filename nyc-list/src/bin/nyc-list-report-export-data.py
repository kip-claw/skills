#!/usr/bin/env python3
"""Snapshot the NYC list Google Sheet into a JSON file for kip-claw, with geocoding."""
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request


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


def geocode(address: str, api_key: str) -> dict | None:
    """Geocode an address using the Google Geocoding API."""
    url = (
        "https://maps.googleapis.com/maps/api/geocode/json"
        f"?address={urllib.parse.quote(address)}&key={api_key}"
    )
    with urllib.request.urlopen(url, timeout=15) as resp:
        data = json.loads(resp.read())
    if data.get("status") == "OK" and data.get("results"):
        loc = data["results"][0]["geometry"]["location"]
        return {"lat": loc["lat"], "lng": loc["lng"]}
    return None


def load_geocache(path: str) -> dict:
    """Load the geocode cache from disk."""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_geocache(path: str, cache: dict) -> None:
    """Save the geocode cache to disk."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)
        f.write("\n")


def main() -> int:
    if len(sys.argv) != 5:
        print(
            "Usage: nyc-list-data-export-core.py <json_path> <geocache_path> <sheet_id> <gog_account>",
            file=sys.stderr,
        )
        return 2

    json_path, geocache_path, sheet_id, gog_account = sys.argv[1:5]
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        print("GOOGLE_MAPS_API_KEY not set", file=sys.stderr)
        return 1

    # Read the sheet
    rows = gog_read(gog_account, sheet_id, "List!A2:G")
    headers = ["name", "address", "isDecent", "isRecommended", "isElite", "isClosed", "notes"]

    places = []
    for row in rows:
        padded = row + [""] * (len(headers) - len(row))
        places.append({h: padded[i] for i, h in enumerate(headers)})

    # Load geocache and geocode missing addresses
    cache = load_geocache(geocache_path)
    geocoded_count = 0

    for place in places:
        address = place["address"].strip()
        if not address:
            place["lat"] = None
            place["lng"] = None
            continue

        if address in cache:
            place["lat"] = cache[address]["lat"]
            place["lng"] = cache[address]["lng"]
        else:
            coords = geocode(address, api_key)
            if coords:
                cache[address] = coords
                place["lat"] = coords["lat"]
                place["lng"] = coords["lng"]
                geocoded_count += 1
                time.sleep(0.05)  # Light throttle
            else:
                print(f"Warning: could not geocode '{address}'", file=sys.stderr)
                place["lat"] = None
                place["lng"] = None

    # Save updated cache
    save_geocache(geocache_path, cache)

    # Write output
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(places, f, indent=2)
        f.write("\n")

    print(f"Wrote {len(places)} places ({geocoded_count} newly geocoded)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
