"""Final step: build ../public/file.json from the scraped offices.

Input, in priority order:
  offices.csv        from scan_ids.py / fetch_json.py (only general_delivery rows used)
  scraped_info.csv   legacy format from the 2022 scrape

Coordinates come from, in order: the scrape itself (lat/lng columns), the
existing public/file.json (matched by USPS URL), then a geocoder: Google if
MAPS_API_KEY is set in the environment, else ArcGIS, else OpenStreetMap.

Usage:  MAPS_API_KEY=... python geocode_format.py [--input offices.csv]
"""
import argparse
import csv
import json
import os
import time

import geocoder
import requests

from common import DETAIL_URL, HERE, PUBLIC_GEOJSON, clean, clean_name

GOOGLE_KEY = os.environ.get("MAPS_API_KEY")


def read_offices(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    if rows and "general_delivery" in rows[0]:
        for r in rows:
            if str(r["general_delivery"]).lower() in ("true", "1", "yes"):
                yield {
                    "name": clean_name(r["name"]), "address": clean(r["address"]),
                    "url": DETAIL_URL.format(r["location_id"]),
                    "coords": [float(r["lng"]), float(r["lat"])] if r.get("lat") and r.get("lng") else None,
                }
    else:  # legacy scraped_info.csv
        for r in rows:
            yield {"name": clean_name(r["placename"]), "address": clean(r["address"]),
                   "url": r["url"].strip(), "coords": None}


def existing_coords():
    if not PUBLIC_GEOJSON.exists():
        return {}
    with PUBLIC_GEOJSON.open() as f:
        return {ft["properties"]["url"].strip(): ft["geometry"]["coordinates"]
                for ft in json.load(f).get("features", [])}


def geocode(address, session):
    attempts = []
    if GOOGLE_KEY:
        attempts.append(lambda: geocoder.google(address, session=session, key=GOOGLE_KEY))
    attempts += [lambda: geocoder.arcgis(address, session=session),
                 lambda: geocoder.osm(address, session=session)]
    for attempt in attempts:
        try:
            r = attempt()
            if r.ok and r.latlng:
                return [round(r.latlng[1], 7), round(r.latlng[0], 7)]  # GeoJSON [lng, lat]
        except Exception as exc:
            print(f"  geocoder error: {exc}")
        time.sleep(0.2)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=None)
    args = ap.parse_args()
    path = args.input or (HERE / "offices.csv" if (HERE / "offices.csv").exists() else HERE / "scraped_info.csv")

    seen, offices = set(), []
    for o in read_offices(path):
        if o["url"] in seen:
            continue
        seen.add(o["url"])
        offices.append(o)
    print(f"{len(offices)} General Delivery offices in {path}")

    known = existing_coords()
    features, failed, geocoded = [], [], 0
    with requests.Session() as session:
        for i, o in enumerate(offices, 1):
            coords = o["coords"] or known.get(o["url"])
            if not coords:
                coords = geocode(o["address"], session)
                geocoded += 1
            if not coords:
                failed.append(o)
                print(f"[{i}/{len(offices)}] FAILED {o['address']}")
                continue
            features.append({"type": "Feature",
                             "geometry": {"type": "Point", "coordinates": [round(float(c), 7) for c in coords]},
                             "properties": {"store_id": len(features), "name": o["name"],
                                            "address": o["address"], "url": o["url"]}})
            if i % 100 == 0:
                print(f"[{i}/{len(offices)}]")

    with PUBLIC_GEOJSON.open("w") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f, indent=1)
    print(f"wrote {len(features)} features to {PUBLIC_GEOJSON} ({geocoded} geocoded, {len(failed)} failed)")
    for o in failed:
        print("  ", o["url"], o["address"])


if __name__ == "__main__":
    main()
