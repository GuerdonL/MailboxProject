"""Fast path, step A: capture the JSON request the USPS location finder makes.

Opens the finder in a real Chrome, turns on the General Delivery filter,
searches one ZIP, and records every XHR/fetch request that went to the
USPS tools REST services along with its response. The capture is saved to
api_capture.json and used by fetch_json.py to replay searches for other ZIPs
without loading any pages.

Usage:  python probe_api.py [--zip 94704] [--headed]

Run this once, then look at api_capture.json: the entry whose response
contains post office names/addresses is the one to use. fetch_json.py picks
it automatically but prints which one it chose.
"""
import argparse
import json
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from browser import make_driver, check_blocked, performance_requests, response_body
from common import FINDER_URL, HERE, save_json

CAPTURE_FILE = HERE / "api_capture.json"

# Same selectors the original scraper used. If USPS changes the page, the
# script falls back to asking you to do the search by hand (--headed).
FORM_ID = "city-state-input"
SEARCH_ID = "searchLocations"
SHOW_FILTERS_XPATH = "/html/body/div[2]/div/div[2]/div[3]/div[2]/div/div[4]/div[2]/p/a"
GEN_MAIL_XPATH = "/html/body/div[2]/div/div[2]/div[3]/div[3]/div[2]/div[1]/label[3]"


def automated_search(driver, zip_code):
    wait = WebDriverWait(driver, 15)
    wait.until(EC.presence_of_element_located((By.XPATH, SHOW_FILTERS_XPATH))).click()
    wait.until(EC.element_to_be_clickable((By.XPATH, GEN_MAIL_XPATH))).click()
    form = driver.find_element(By.ID, FORM_ID)
    form.clear()
    form.send_keys(zip_code)
    wait.until(EC.element_to_be_clickable((By.ID, SEARCH_ID))).click()
    time.sleep(4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", default="94704")
    ap.add_argument("--headed", action="store_true", help="show the browser window")
    args = ap.parse_args()

    driver = make_driver(headless=not args.headed, capture_network=True)
    try:
        driver.execute_cdp_cmd("Network.enable", {})
        driver.get(FINDER_URL)
        check_blocked(driver)
        try:
            automated_search(driver, args.zip)
        except Exception as exc:
            print(f"Automated search failed ({exc.__class__.__name__}).")
            if args.headed:
                input("Turn on the General Delivery filter, search a ZIP, then press Enter here... ")
            else:
                print("Re-run with --headed and do the search by hand.")
                return

        captured = []
        for request_id, req in performance_requests(driver):
            url = req.get("url", "")
            if "usps.com" not in url:
                continue
            body = response_body(driver, request_id)
            captured.append({
                "url": url,
                "method": req.get("method"),
                "headers": req.get("headers", {}),
                "postData": req.get("postData"),
                "response_preview": (body or "")[:3000],
                "response_length": len(body or ""),
                "mentions_general_delivery": "general delivery" in (body or "").lower(),
                "probe_zip": args.zip,
            })
        save_json(CAPTURE_FILE, captured)
        print(f"Captured {len(captured)} USPS requests -> {CAPTURE_FILE}")
        for c in captured:
            flag = "  <-- candidate" if c["mentions_general_delivery"] or "POLocator" in c["url"] else ""
            print(f"  {c['method']} {c['url'][:100]}  ({c['response_length']} bytes){flag}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
