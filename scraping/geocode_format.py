"""Step 3: geocode scraped_info.csv and write the site's GeoJSON.

Reads scraped_info.csv, cleans and de-duplicates rows (by USPS URL), geocodes
each address, and writes ../public/file.json as a GeoJSON FeatureCollection
with properties {store_id, name, address, url}.

Coordinates already present in public/file.json are reused, so only new
locations hit the geocoder.

Geocoders, in order: Google (if MAPS_API_KEY is set in the environment),
ArcGIS, OpenStreetMap/Nominatim. No key is ever read from this file.

Usage:  MAPS_API_KEY=... python geocode_format.py
"""
import csv
import json
import os
import re
import time
from pathlib import Path

import geocoder
import requests

HERE = Path(__file__).resolve().parent
IN_FILE = HERE / "scraped_info.csv"
OUT_FILE = HERE.parent / "public" / "file.json"
GOOGLE_KEY = os.environ.get("MAPS_API_KEY")


def clean(text):
    text = text.replace("™", "").replace("—", "-")
    return re.sub(r"\s+", " ", text).strip()


def clean_name(name):
    return clean(name).replace(" - Post Office", " Post Office")


def load_existing_coords():
    if not OUT_FILE.exists():
        return {}
    with OUT_FILE.open() as f:
        data = json.load(f)
    return {
        feat["properties"]["url"].strip(): feat["geometry"]["coordinates"]
        for feat in data.get("features", [])
        if feat.get("geometry", {}).get("coordinates")
    }


def geocode(address, session):
    attempts = []
    if GOOGLE_KEY:
        attempts.append(lambda: geocoder.google(address, session=session, key=GOOGLE_KEY))
    attempts.append(lambda: geocoder.arcgis(address, session=session))
    attempts.append(lambda: geocoder.osm(address, session=session))
    for attempt in attempts:
        try:
            result = attempt()
            if result.ok and result.latlng:
                lat, lng = result.latlng
                return [round(lng, 7), round(lat, 7)]  # GeoJSON is [lng, lat]
        except Exception as exc:  # network or provider error; try the next one
            print(f"  geocoder error: {exc}")
        time.sleep(0.2)
    return None


def main():
    with IN_FILE.open(newline="") as f:
        rows = list(csv.DictReader(f))

    seen = set()
    locations = []
    for row in rows:
        url = row["url"].strip()
        if not url or url in seen:
            continue
        seen.add(url)
        locations.append({
            "name": clean_name(row["placename"]),
            "address": clean(row["address"]),
            "url": url,
        })

    existing = load_existing_coords()
    features = []
    failed = []
    with requests.Session() as session:
        for i, loc in enumerate(locations, 1):
            coords = existing.get(loc["url"]) or geocode(loc["address"], session)
            if not coords:
                failed.append(loc)
                print(f"[{i}/{len(locations)}] FAILED {loc['address']}")
                continue
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": coords},
                "properties": {"store_id": len(features), **loc},
            })
            print(f"[{i}/{len(locations)}] {loc['name']}")

    with OUT_FILE.open("w") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f, indent=1)

    print(f"wrote {len(features)} features to {OUT_FILE}")
    if failed:
        print(f"{len(failed)} addresses could not be geocoded:")
        for loc in failed:
            print("  ", loc["url"], loc["address"])


if __name__ == "__main__":
    main()
