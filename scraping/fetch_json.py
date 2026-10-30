"""Fast path, step B: replay the captured locator request for every ZIP.

Uses api_capture.json (from probe_api.py) as a template: the probe ZIP is
swapped for each ZIP in geo-data.csv and the request is issued with fetch()
inside a real Chrome page so USPS's cookies and anti-bot tokens apply. Each
response is parsed generically for post-office records (id, name, address,
lat/lng, services), and every office that lists General Delivery is written
to offices.csv. Raw responses are kept in raw_responses.jsonl so the parse can
be re-run offline if the field names turn out to differ.

Usage:  python fetch_json.py [--zips geo-data.csv] [--headed] [--all-offices]

Resumable: ZIPs already in zips_done.txt are skipped.
"""
import argparse
import csv
import json
import re
import time

from browser import make_driver, check_blocked, fetch_in_page, polite_sleep, BlockedError
from common import (FINDER_URL, HERE, ResultsWriter, clean, clean_name, load_json)

CAPTURE_FILE = HERE / "api_capture.json"
RAW_FILE = HERE / "raw_responses.jsonl"
ZIPS_DONE = HERE / "zips_done.txt"

ID_KEYS = ("locationID", "locationId", "location_id", "id")
NAME_KEYS = ("locationName", "name", "locationname")
ADDR_KEYS = ("address1", "address", "addressLineOne", "streetAddress")
CITY_KEYS = ("city",)
STATE_KEYS = ("state",)
ZIP_KEYS = ("zip5", "zip", "zipCode", "postalCode")
LAT_KEYS = ("latitude", "lat")
LNG_KEYS = ("longitude", "lng", "lon")


def pick_template(captured):
    """Choose the request most likely to be the locator search."""
    def score(c):
        s = 0
        if "POLocator" in c["url"] or "findLocations" in c["url"]: s += 5
        if c.get("mentions_general_delivery"): s += 3
        if c.get("method") == "POST": s += 1
        s += min(c.get("response_length", 0) / 10000, 3)
        return s
    return max(captured, key=score)


def substitute_zip(template, zip_code):
    probe = template["probe_zip"]
    url = template["url"].replace(probe, zip_code)
    body = template.get("postData")
    if body:
        body = body.replace(probe, zip_code)
    return url, body


def first(d, keys):
    for k in keys:
        for dk, v in d.items():
            if dk.lower() == k.lower() and v not in (None, ""):
                return v
    return None


def walk(obj):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk(v)


def extract_offices(payload):
    """Find dicts that look like post offices anywhere in the JSON."""
    for d in walk(payload):
        loc_id = first(d, ID_KEYS)
        name = first(d, NAME_KEYS)
        addr = first(d, ADDR_KEYS)
        if not (loc_id and name and addr):
            continue
        subtree = json.dumps(d).lower()
        parts = [clean(str(addr)), clean(str(first(d, CITY_KEYS) or "")),
                 clean(str(first(d, STATE_KEYS) or "")), clean(str(first(d, ZIP_KEYS) or ""))]
        yield {
            "location_id": str(loc_id),
            "name": clean_name(str(name)),
            "address": re.sub(r"\s+", " ", f"{parts[0]} {parts[1]}, {parts[2]} {parts[3]}").strip(" ,"),
            "lat": first(d, LAT_KEYS) or "",
            "lng": first(d, LNG_KEYS) or "",
            "general_delivery": "general delivery" in subtree,
            "source": "api",
        }


def zips_from(path):
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        col = "zipcode" if "zipcode" in reader.fieldnames else reader.fieldnames[0]
        seen = set()
        for row in reader:
            z = row[col].strip().zfill(5)
            if z not in seen:
                seen.add(z)
                yield z


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zips", default=str(HERE / "geo-data.csv"))
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--all-offices", action="store_true",
                    help="record every office, not only General Delivery ones")
    args = ap.parse_args()

    captured = load_json(CAPTURE_FILE)
    if not captured:
        raise SystemExit("api_capture.json missing: run probe_api.py first")
    template = pick_template(captured)
    print(f"Using template: {template['method']} {template['url'][:120]}")

    done = set(ZIPS_DONE.read_text().split()) if ZIPS_DONE.exists() else set()
    zips = [z for z in zips_from(args.zips) if z not in done]
    print(f"{len(zips)} ZIPs to search ({len(done)} already done)")

    writer = ResultsWriter()
    driver = make_driver(headless=not args.headed)
    blocked_streak = 0
    try:
        driver.get(FINDER_URL)
        check_blocked(driver)
        with RAW_FILE.open("a") as raw, ZIPS_DONE.open("a") as done_fh:
            for i, z in enumerate(zips, 1):
                url, body = substitute_zip(template, z)
                try:
                    res = fetch_in_page(driver, url, template["method"], template.get("headers"), body)
                    blocked_streak = 0
                except BlockedError:
                    blocked_streak += 1
                    wait = min(60 * blocked_streak, 600)
                    print(f"blocked; backing off {wait}s and reloading")
                    time.sleep(wait)
                    driver.get(FINDER_URL)
                    continue
                if res["status"] != 200:
                    print(f"{z}: HTTP {res['status']}")
                    continue
                raw.write(json.dumps({"zip": z, "body": res["text"]}) + "\n")
                try:
                    payload = json.loads(res["text"])
                except json.JSONDecodeError:
                    print(f"{z}: non-JSON response ({len(res['text'])} bytes)")
                    continue
                n = 0
                for office in extract_offices(payload):
                    if office["general_delivery"] or args.all_offices:
                        writer.write(office)
                        n += 1
                done_fh.write(z + "\n")
                done_fh.flush()
                if i % 25 == 0 or n:
                    print(f"[{i}/{len(zips)}] {z}: {n} offices  (total GD so far: {len(writer.done)})")
                polite_sleep()
    finally:
        writer.close()
        driver.quit()


if __name__ == "__main__":
    main()
