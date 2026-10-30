"""Shared helpers for the scraping scripts."""
import csv
import json
import re
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PUBLIC_GEOJSON = HERE.parent / "public" / "file.json"

# Output of scan_ids.py and fetch_json.py. One row per post office seen.
RESULTS_FILE = HERE / "offices.csv"
RESULT_FIELDS = [
    "location_id", "name", "address", "lat", "lng", "general_delivery", "source",
]

DETAIL_URL = "https://tools.usps.com/find-location.htm?location={}"
FINDER_URL = "https://tools.usps.com/find-location.htm"

# USPS redirects non-browser or rate-limited clients here.
BLOCK_MARKERS = ("webtools-msg", "automated access", "access denied", "/root/global/server_responses")


def clean(text):
    text = (text or "").replace("™", "").replace("—", "-")
    return re.sub(r"\s+", " ", text).strip()


def clean_name(name):
    name = clean(name)
    name = name.replace(" - Post Office", " Post Office")
    if not re.search(r"post office|station|branch|annex|cpu|village|finance", name, re.I):
        name = f"{name} Post Office"
    return name


class ResultsWriter:
    """Append-only, thread-safe CSV writer that knows what has been done."""

    def __init__(self, path=RESULTS_FILE):
        self.path = Path(path)
        self.lock = threading.Lock()
        self.done = set()
        new_file = not self.path.exists() or self.path.stat().st_size == 0
        if not new_file:
            with self.path.open(newline="") as f:
                for row in csv.DictReader(f):
                    self.done.add(str(row["location_id"]))
        self.fh = self.path.open("a", newline="")
        self.writer = csv.DictWriter(self.fh, fieldnames=RESULT_FIELDS)
        if new_file:
            self.writer.writeheader()
            self.fh.flush()

    def write(self, row):
        with self.lock:
            if str(row["location_id"]) in self.done:
                return
            self.done.add(str(row["location_id"]))
            self.writer.writerow({k: row.get(k, "") for k in RESULT_FIELDS})
            self.fh.flush()

    def close(self):
        self.fh.close()


class Progress:
    def __init__(self, total, every=50):
        self.total, self.every = total, every
        self.n = 0
        self.hits = 0
        self.start = time.time()
        self.lock = threading.Lock()

    def tick(self, hit=False):
        with self.lock:
            self.n += 1
            self.hits += int(hit)
            if self.n % self.every == 0 or self.n == self.total:
                elapsed = time.time() - self.start
                rate = self.n / elapsed if elapsed else 0
                remaining = (self.total - self.n) / rate if rate else 0
                print(f"{self.n}/{self.total}  {self.hits} GD offices  "
                      f"{rate:.1f}/s  ~{remaining/60:.0f} min left", flush=True)


def load_json(path, default=None):
    path = Path(path)
    if not path.exists():
        return default
    with path.open() as f:
        return json.load(f)


def save_json(path, data):
    with Path(path).open("w") as f:
        json.dump(data, f, indent=1)
