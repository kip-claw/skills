---
name: geocoder
description: Geocode addresses into latitude/longitude coordinates using the Google Geocoding API. Use when asked to convert an address to coordinates, find a location's lat/lng, or geocode places.
metadata: {"openclaw": {"emoji": "📍", "requires": {"env": ["GOOGLE_MAPS_API_KEY"]}}}
---

# Geocoder (Google Geocoding API)

Converts street addresses into latitude/longitude coordinates using the Google Maps Geocoding API.

## API Endpoint

```
https://maps.googleapis.com/maps/api/geocode/json?address={encoded_address}&key={GOOGLE_MAPS_API_KEY}
```

## Commands

### Geocode a single address

```bash
curl -s "https://maps.googleapis.com/maps/api/geocode/json?address=$(python3 -c 'import urllib.parse; print(urllib.parse.quote("25 Avenue A, New York, NY 10009"))')&key=$GOOGLE_MAPS_API_KEY" \
  | python3 -c "import sys,json; r=json.load(sys.stdin)['results'][0]['geometry']['location']; print(f\"{r['lat']},{r['lng']}\")"
```

### Geocode with Python

```python
import json
import os
import urllib.request
import urllib.parse

def geocode(address: str) -> dict | None:
    api_key = os.environ["GOOGLE_MAPS_API_KEY"]
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={urllib.parse.quote(address)}&key={api_key}"
    with urllib.request.urlopen(url) as resp:
        data = json.loads(resp.read())
    if data["status"] == "OK" and data["results"]:
        loc = data["results"][0]["geometry"]["location"]
        return {"lat": loc["lat"], "lng": loc["lng"]}
    return None
```

## Response Format

The API returns a JSON object. The coordinates are at:
```
results[0].geometry.location.lat
results[0].geometry.location.lng
```

## Workflow Rules

- **API key**: Read from `GOOGLE_MAPS_API_KEY` environment variable (stored in `~/.openclaw/.env`)
- **Rate limits**: Google allows 50 requests/second on standard tier
- **Caching**: Cache results to avoid repeated lookups for the same address
- **Error handling**: Check `status` field — `OK` means success, `ZERO_RESULTS` means no match
- **Address format**: Use full addresses for best accuracy (e.g., "25 Avenue A, New York, NY 10009")

## Notes

- Requires a Google Cloud project with the Geocoding API enabled
- Billed per request after the free $200/month credit
- The `GOOGLE_MAPS_API_KEY` should have Geocoding API access enabled
