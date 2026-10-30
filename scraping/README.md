# Rebuilding the General Delivery location list

USPS refuses anything that doesn't look like a real browser (non-browser
clients get redirected to a "no automated access" page), so everything here
drives a real Chrome through Selenium on your own machine.

```sh
cd scraping
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt     # Chrome must be installed; Selenium fetches chromedriver
```

There are two ways to get the data. Try the fast path first.

## Fast path: replay the finder's JSON API (minutes to an hour)

The location-finder page is a front end over a JSON endpoint. We capture the
request it makes once, then replay it for every ZIP from inside the page so
USPS's own cookies and tokens apply. One call returns a batch of offices with
addresses, usually coordinates, and their services, so there is no per-office
page load and no geocoding.

```sh
python probe_api.py --headed            # one search; writes api_capture.json
python fetch_json.py                    # replays for every ZIP in geo-data.csv -> offices.csv
```

`probe_api.py` prints the requests it captured and flags the likely locator
call. If the automated clicks fail (USPS changed the page), it waits for you to
do the search by hand in the window. `fetch_json.py` keeps every raw response
in `raw_responses.jsonl`, so if the field names differ from what it expects,
the parse can be fixed and re-run without touching USPS again.

## Fallback: scan the location-ID range in parallel (about 1–2 hours)

Every post office has a numeric location ID; the valid ones cluster in roughly
1,350,000–1,390,000 (about 14k real offices, most not General Delivery). This
loads each detail page with a pool of Chrome workers and keeps the ones whose
services mention General Delivery.

```sh
python scan_ids.py --sample                      # ~40 IDs across the range: confirm bounds
python scan_ids.py --ids ids.csv --all-offices   # sanity check: CHAMA (1357592) must come out general_delivery=True
python scan_ids.py --start 1350000 --end 1390000 --workers 4
```

Progress is saved continuously (`offices.csv`, `scanned_ids.txt`); Ctrl-C and
re-run to resume. If a worker hits the automated-access page it backs off
(60 s, 120 s, …) and restarts its browser; if that happens often, drop
`--workers` or run `--headed`. 40k IDs × ~1 s / 4 workers ≈ 3 hours worst
case; use `--sample` output to tighten `--start/--end` first.

## Build the site data

```sh
MAPS_API_KEY=... python geocode_format.py        # -> ../public/file.json
```

Coordinates are taken from the scrape when present, otherwise from the
existing `public/file.json`, otherwise geocoded (Google if `MAPS_API_KEY` is
set, else ArcGIS, else OpenStreetMap). Commit `public/file.json` and the merge
workflow deploys it.

## Files

| file | what |
|---|---|
| `offices.csv` | scraped offices: id, name, address, lat, lng, general_delivery, source |
| `geo-data.csv` | one ZIP per US county; search seeds for the fast path |
| `ids.csv`, `scraped_info.csv` | the 2022 scrape (568 IDs / 300 offices), kept for reference; `scan_ids.py --ids ids.csv` re-checks them |
| `api_capture.json`, `raw_responses.jsonl`, `zips_done.txt`, `scanned_ids.txt` | working files, git-ignored |
