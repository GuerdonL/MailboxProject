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
- `scraping/` — the Python pipeline that builds `public/file.json` by scraping the USPS
  location finder with a real Chrome (Selenium). See `scraping/README.md`; it has a fast
  JSON-replay path and a parallel ID-range scanner, both resumable.

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

See `scraping/README.md`. In short: run the scraper on your own machine (USPS blocks
non-browser clients), then `MAPS_API_KEY=... python geocode_format.py` and commit the
updated `public/file.json`; the merge workflow deploys it.

## License

MIT — see `LICENSE`.
