"""Chrome/Selenium helpers shared by the scrapers."""
import json
import random
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from common import BLOCK_MARKERS


class BlockedError(Exception):
    """USPS served its automated-access page instead of content."""


def make_driver(headless=True, capture_network=False):
    opts = Options()
    if headless:
        # Headless Chrome is a little more likely to be flagged; use --headed
        # on the scripts if you see BlockedError frequently.
        opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1280,900")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--blink-settings=imagesEnabled=false")
    opts.page_load_strategy = "eager"
    if capture_network:
        opts.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(45)
    return driver


def check_blocked(driver):
    url = (driver.current_url or "").lower()
    if any(m in url for m in BLOCK_MARKERS):
        raise BlockedError(url)
    try:
        body = driver.find_element("tag name", "body").text[:400].lower()
    except Exception:
        return
    if "automated access" in body or "access denied" in body:
        raise BlockedError(body[:80])


def polite_sleep(base=0.4, jitter=0.6):
    time.sleep(base + random.random() * jitter)


def fetch_in_page(driver, url, method="GET", headers=None, body=None, timeout=30):
    """Run fetch() inside the current page so cookies/anti-bot tokens apply."""
    driver.set_script_timeout(timeout)
    script = """
      const [url, method, headers, body, done] = arguments;
      const opts = {method, headers, credentials: 'include'};
      if (body !== null && body !== undefined) opts.body = body;
      fetch(url, opts)
        .then(async (r) => done({status: r.status, url: r.url, text: await r.text()}))
        .catch((e) => done({status: 0, error: String(e)}));
    """
    result = driver.execute_async_script(script, url, method, headers or {}, body)
    if result.get("status") == 0:
        raise RuntimeError(result.get("error", "fetch failed"))
    if any(m in (result.get("url") or "").lower() for m in BLOCK_MARKERS):
        raise BlockedError(result.get("url"))
    return result


def performance_requests(driver):
    """Yield (requestId, request dict) for XHR/fetch calls seen so far."""
    for entry in driver.get_log("performance"):
        try:
            msg = json.loads(entry["message"])["message"]
        except Exception:
            continue
        if msg.get("method") != "Network.requestWillBeSent":
            continue
        params = msg["params"]
        if params.get("type") not in ("XHR", "Fetch"):
            continue
        yield params["requestId"], params["request"]


def response_body(driver, request_id):
    try:
        res = driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": request_id})
        return res.get("body")
    except Exception:
        return None
