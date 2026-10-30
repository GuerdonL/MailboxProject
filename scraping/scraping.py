"""Step 2: scrape name and address for every location ID in ids.csv.

Reads ids.csv (one USPS location ID per line, from find_urls.py) and writes
scraped_info.csv with columns placename,url,address. Already-scraped IDs are
skipped, so the script can be stopped and resumed.

Usage:  python scraping.py
"""
import csv
from pathlib import Path

import bs4
from selenium import webdriver

HERE = Path(__file__).resolve().parent
IDS_FILE = HERE / "ids.csv"
OUT_FILE = HERE / "scraped_info.csv"
URL_TEMPLATE = "https://tools.usps.com/find-location.htm?location={}"
FIELDS = ["placename", "url", "address"]


def already_scraped():
    if not OUT_FILE.exists():
        return set()
    with OUT_FILE.open(newline="") as f:
        return {row["url"].strip() for row in csv.DictReader(f)}


def main():
    with IDS_FILE.open() as f:
        ids = [line.strip() for line in f if line.strip()]
    done = already_scraped()
    write_header = not OUT_FILE.exists() or OUT_FILE.stat().st_size == 0

    browser = webdriver.Chrome()
    try:
        with OUT_FILE.open("a", newline="") as out:
            writer = csv.DictWriter(out, fieldnames=FIELDS)
            if write_header:
                writer.writeheader()
            for i, location_id in enumerate(ids, 1):
                url = URL_TEMPLATE.format(location_id)
                if url in done:
                    continue
                browser.get(url)
                soup = bs4.BeautifulSoup(browser.page_source, "html.parser")
                name_el = soup.find("h1", {"class": "normal"})
                addr_el = soup.find("div", {"class": "address-wrapper"})
                if not name_el or not addr_el:
                    print(f"[{i}/{len(ids)}] could not parse {url}")
                    continue
                writer.writerow({
                    "placename": " ".join(name_el.get_text().split()),
                    "url": url,
                    "address": " ".join(addr_el.get_text().split()),
                })
                out.flush()
                print(f"[{i}/{len(ids)}] {url}")
    finally:
        browser.quit()


if __name__ == "__main__":
    main()
