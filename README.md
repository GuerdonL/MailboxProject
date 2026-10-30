# The Mailbox Project

A simple utility website to help people find the nearest US post office that offers
[General Delivery](https://faq.usps.com/s/article/What-is-General-Delivery). Largely built
as a response to the overturning of Roe v. Wade, the idea is to help in the acquisition of
abortion medication without having it delivered to a home address.

Live at: https://themailboxproject.org

## How it works

- `public/` — a static site (vanilla JS + Google Maps) hosted on Firebase Hosting. It loads
  `public/file.json`, a GeoJSON list of post offices, lets the visitor type an address, and
  ranks the 25 closest locations by driving distance.
- `scraping/` — the Python pipeline that builds `public/file.json`:
  1. `find_urls.py` searches the USPS location finder (General Delivery filter on) by ZIP
     code and writes `ids.csv`.
  2. `scraping.py` fetches the name and address for each ID into `scraped_info.csv`.
  3. `geocode_format.py` geocodes the addresses and writes `public/file.json`.

## API keys

No API keys are committed to this repository.

- **Google Maps** — the key lives in the `MAPS_API_KEY` GitHub Actions secret and is
  substituted for the `__MAPS_API_KEY__` placeholder in `public/index.html` at deploy time.
  Because the key is necessarily visible in the browser, restrict it in Google Cloud to
  HTTP referrers (`themailboxproject.org`, `*.web.app`, `*.firebaseapp.com`) and to the
  APIs the site uses: Maps JavaScript, Places, Distance Matrix, Street View Static.
- **Firebase web config** (`public/firebase.js`) is public by design.

## Running locally

```sh
MAPS_API_KEY=your-key ./scripts/serve-local.sh      # serves http://localhost:8000
```

The script copies `public/` to a temp directory and injects the key there, so nothing
secret is written into the repository.

## Refreshing the location data

```sh
cd scraping
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt            # needs Chrome + chromedriver for Selenium
python find_urls.py                        # slow: one USPS search per county ZIP
python scraping.py                         # resumable; skips already-scraped IDs
MAPS_API_KEY=your-key python geocode_format.py   # reuses existing coordinates
```

Commit the updated `public/file.json`; the merge workflow deploys it.

## License

MIT — see `LICENSE`.
