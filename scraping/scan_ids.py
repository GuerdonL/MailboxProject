"""Fallback path: scan the USPS location-ID range with a pool of Chrome workers.

Every location detail page (find-location.htm?location=<id>) is loaded,
checked for existence, and searched for "General Delivery" in its services.
Offices that offer it are written to offices.csv (use --all-offices to keep
every office). Resumable: IDs already in offices.csv or scanned_ids.txt are
skipped, so you can Ctrl-C and restart freely.

Usage:
  python scan_ids.py --sample                    # probe the range edges first
  python scan_ids.py --start 1350000 --end 1390000 --workers 5
  python scan_ids.py --ids ids.csv               # scan a specific list instead

Each worker owns one Chrome. If USPS serves its automated-access page, that
worker backs off (60s, 120s, ...) and restarts its browser. Start with
--workers 4; raise it only if you see no blocks.
"""
import argparse
import queue
import re
import threading
import time

import bs4
from selenium.common.exceptions import WebDriverException

from browser import make_driver, check_blocked, polite_sleep, BlockedError
from common import DETAIL_URL, HERE, Progress, ResultsWriter, clean, clean_name

SCANNED_FILE = HERE / "scanned_ids.txt"   # every ID visited, hit or miss
LATLNG_RE = re.compile(r'"?(?:latitude|lat)"?\s*[:=]\s*"?(-?\d{1,2}\.\d+)"?.{0,80}?"?(?:longitude|lng|lon)"?\s*[:=]\s*"?(-?\d{1,3}\.\d+)"?',
                       re.I | re.S)


def parse_detail(html):
    soup = bs4.BeautifulSoup(html, "html.parser")
    name_el = soup.find("h1", {"class": "normal"}) or soup.find("h1")
    addr_el = soup.find("div", {"class": "address-wrapper"})
    if not name_el or not addr_el:
        return None  # no such location
    # Match an element whose own text is "General Delivery" (a service list
    # entry), not any mention anywhere on the page, to avoid nav/footer hits.
    has_gd = any(el.get_text(strip=True).lower().rstrip(":") == "general delivery"
                 for el in soup.find_all(["li", "td", "span", "p", "div", "label"]))
    m = LATLNG_RE.search(html)
    return {
        "name": clean_name(name_el.get_text()),
        "address": clean(addr_el.get_text()),
        "lat": m.group(1) if m else "",
        "lng": m.group(2) if m else "",
        "general_delivery": has_gd,
    }


class Worker(threading.Thread):
    def __init__(self, idx, ids, writer, scanned_fh, scanned_lock, progress, headless, all_offices):
        super().__init__(daemon=True, name=f"worker-{idx}")
        self.ids, self.writer, self.progress = ids, writer, progress
        self.scanned_fh, self.scanned_lock = scanned_fh, scanned_lock
        self.headless, self.all_offices = headless, all_offices
        self.driver = None
        self.block_streak = 0

    def restart(self):
        if self.driver:
            try: self.driver.quit()
            except Exception: pass
        self.driver = make_driver(headless=self.headless)

    def run(self):
        self.restart()
        while True:
            try:
                loc_id = self.ids.get_nowait()
            except queue.Empty:
                break
            try:
                self.scan(loc_id)
                self.block_streak = 0
            except BlockedError:
                self.block_streak += 1
                wait = min(60 * self.block_streak, 900)
                print(f"[{self.name}] blocked on {loc_id}; sleeping {wait}s", flush=True)
                self.ids.put(loc_id)
                time.sleep(wait)
                self.restart()
            except WebDriverException as exc:
                print(f"[{self.name}] browser error on {loc_id}: {exc.__class__.__name__}; restarting", flush=True)
                self.ids.put(loc_id)
                time.sleep(5)
                self.restart()
            finally:
                self.ids.task_done()
        try: self.driver.quit()
        except Exception: pass

    def scan(self, loc_id):
        self.driver.get(DETAIL_URL.format(loc_id))
        check_blocked(self.driver)
        info = parse_detail(self.driver.page_source)
        hit = bool(info and info["general_delivery"])
        if info and (hit or self.all_offices):
            self.writer.write({"location_id": loc_id, "source": "scan", **info})
        with self.scanned_lock:
            self.scanned_fh.write(f"{loc_id}\n")
            self.scanned_fh.flush()
        self.progress.tick(hit)
        polite_sleep()


def id_list(args):
    if args.ids:
        with open(args.ids) as f:
            return [line.strip() for line in f if line.strip().isdigit()]
    if args.sample:
        step = max((args.end - args.start) // 40, 1)
        return [str(i) for i in range(args.start, args.end + 1, step)]
    return [str(i) for i in range(args.start, args.end + 1)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=1350000)
    ap.add_argument("--end", type=int, default=1390000)
    ap.add_argument("--ids", help="file with one location ID per line (overrides range)")
    ap.add_argument("--sample", action="store_true", help="scan ~40 IDs spread across the range")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--all-offices", action="store_true")
    args = ap.parse_args()

    writer = ResultsWriter()
    scanned = set(SCANNED_FILE.read_text().split()) if SCANNED_FILE.exists() else set()
    todo = [i for i in id_list(args) if i not in scanned and i not in writer.done]
    if args.sample:
        todo = id_list(args)  # always re-probe when sampling
    print(f"{len(todo)} IDs to scan with {args.workers} workers")
    if not todo:
        return

    ids = queue.Queue()
    for i in todo:
        ids.put(i)
    progress = Progress(len(todo), every=25 if args.sample else 100)
    scanned_fh = SCANNED_FILE.open("a")
    lock = threading.Lock()
    workers = [Worker(n, ids, writer, scanned_fh, lock, progress, not args.headed, args.all_offices)
               for n in range(args.workers)]
    for w in workers:
        w.start()
        time.sleep(2)  # stagger browser start-up
    try:
        for w in workers:
            while w.is_alive():
                w.join(1)
    except KeyboardInterrupt:
        print("\nstopping; progress is saved, re-run to resume")
    finally:
        scanned_fh.close()
        writer.close()
    print(f"done: {len(writer.done)} offices in {writer.path}")


if __name__ == "__main__":
    main()
