"""Step 1: collect USPS location IDs for post offices offering General Delivery.

Drives the USPS "Find Locations" tool with the General Delivery filter on,
searching one ZIP code per county (from geo-data.csv), and records every
location ID that appears in the results.

Outputs (in this directory):
  ids.csv          one location ID per line, de-duplicated
  failed_zips.csv  ZIPs whose search timed out, for re-running

Usage:  python find_urls.py
"""
import csv
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

HERE = Path(__file__).resolve().parent
GEO_DATA = HERE / "geo-data.csv"
IDS_FILE = HERE / "ids.csv"
FAILED_FILE = HERE / "failed_zips.csv"

URL = "https://tools.usps.com/find-location.htm"
FORM_ID = "city-state-input"
SEARCH_ID = "searchLocations"
LOCATION_ITEM_XPATHS = [
    "/html/body/div[2]/div/div[2]/div[3]/div[5]/div[2]/div[1]/div[1]/*",
    "/html/body/div[2]/div/div[2]/div[3]/div[5]/div[2]/div[1]/div[2]/*",
]
SHOW_FILTERS_XPATH = "/html/body/div[2]/div/div[2]/div[3]/div[2]/div/div[4]/div[2]/p/a"
GEN_MAIL_XPATH = "/html/body/div[2]/div/div[2]/div[3]/div[3]/div[2]/div[1]/label[3]"


def load_existing(path):
    if not path.exists():
        return set()
    with path.open() as f:
        return {line.strip() for line in f if line.strip()}


def save_set(path, values):
    with path.open("w") as f:
        f.write("\n".join(sorted(values)) + "\n")


def zip_codes():
    with GEO_DATA.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield row["zipcode"].zfill(5)


def search_all(browser, po_ids, failed_zips):
    form = browser.find_element(By.ID, FORM_ID)
    search = browser.find_element(By.ID, SEARCH_ID)
    for zip_code in zip_codes():
        form.clear()
        form.send_keys(zip_code)
        WebDriverWait(browser, 10).until(EC.element_to_be_clickable(search)).click()
        try:
            for xpath in LOCATION_ITEM_XPATHS:
                items = WebDriverWait(browser, 3).until(
                    EC.presence_of_all_elements_located((By.XPATH, xpath))
                )
                for item in items:
                    item_id = item.get_property("id")
                    if item_id:
                        po_ids.add(str(item_id))
        except Exception:
            print(f"timeout on zip {zip_code}")
            failed_zips.add(zip_code)
        else:
            failed_zips.discard(zip_code)
        finally:
            save_set(IDS_FILE, po_ids)
            save_set(FAILED_FILE, failed_zips)
        print(f"{zip_code}: {len(po_ids)} ids so far")


def main():
    po_ids = load_existing(IDS_FILE)
    failed_zips = load_existing(FAILED_FILE)
    browser = webdriver.Chrome()
    try:
        browser.get(URL)
        WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.XPATH, SHOW_FILTERS_XPATH))
        ).click()
        # Toggle the General Delivery filter. (The filter list doesn't always
        # expand on the first click; re-run if the toggle is not visible.)
        WebDriverWait(browser, 10).until(
            EC.element_to_be_clickable((By.XPATH, GEN_MAIL_XPATH))
        ).click()
        search_all(browser, po_ids, failed_zips)
    finally:
        browser.quit()


if __name__ == "__main__":
    main()
