# GoldRock Metal Exchange — Live & Historic Price Chart

A single self-contained `index.html` with a hand-coded canvas chart showing **real**
historic + live spot prices for **Gold, Silver, and Platinum**. No paid or keyed API
anywhere — every data source is a public, keyless endpoint.

## What it does
- **Live spot** for all three metals, refreshed in the browser every 60s from
  `api.gold-api.com` (sends `Access-Control-Allow-Origin: *`, so it works client-side).
- **Real daily history** baked into the page:
  | Metal | Daily source | History back to |
  |-------|--------------|-----------------|
  | Gold | goldprice.org | 1973 daily + monthly to **1915** |
  | Silver | goldprice.org | 1975 daily + monthly to **1915** |
  | Platinum | macrotrends.net (`/economic-data/2540/D`) | **1969** daily |
- Interactive: metal tabs, timeframes (1M / 6M / YTD / 1Y / 5Y / 10Y / MAX),
  hover crosshair + tooltip, animated draw-in, per-metal stat cards
  (open, high, low, change, 52-week range, all-time high).
- GoldRock-branded (real logo, palette, phone, concierge email). No premiums/markup
  language anywhere — differentiates on trust, family-run, everything-in-writing.

## Data sources (all keyless — no API key required)
- `https://api.gold-api.com/price/{XAU,XAG,XPT}` — live spot (JSON, CORS-open).
- `https://data-asg.goldprice.org/GetDataHistorical/USD-{XAU,XAG}/0` — daily gold/silver
  (needs a browser User-Agent + `Referer: https://goldprice.org/`; no CORS, so fetched
  at build time, not in the browser).
- `https://www.macrotrends.net/economic-data/{2540,1333,1470}/D` — platinum daily (2540),
  gold monthly (1333), silver monthly (1470) — used for the pre-daily long tail.

## Note on the data
The sources record a coordinated precious-metals spike the week of **Jan 23–29, 2026**
(gold ≈ $5,327, silver ≈ $115.50, platinum ≈ $2,735), followed by a correction to
current levels. This is confirmed independently across both goldprice.org and
macrotrends, so the all-time-high figures shown reflect that real recorded event —
the chart renders the sources faithfully rather than smoothing them.

## Rebuild
```
python3 ~/goldrock-metals-chart/build/build.py
```
Writes atomically to `~/goldrock-metals-chart/index.html` and the preview mirror
`/tmp/goldrock-metals-chart/index.html` (never overwrites a good file with a broken one).

## Preview
Served from the `/tmp` mirror on port **4490** (preview name `goldrock-metals-chart`):
`python3 -m http.server 4490 --directory /tmp/goldrock-metals-chart`

## Keep it current automatically (optional)
A twice-daily launchd job is prepared but **not installed** (it's a background-persistence
action). To enable:
```
bash ~/goldrock-metals-chart/install-autoupdate.sh
```
Runs the build at 06:00 and 15:15 local time. Disable by unloading the agent
(see the bottom of the install script). Even without it, the page always shows live
spot on load — the schedule only keeps the *historic baseline* current.

## Files
- `build/build.py` — data pipeline (fetch → splice → anchor to live → inject).
- `build/template.html` — the page + chart (placeholders `/*__DATA_JSON__*/0`,
  `/*__META_JSON__*/0`, `__LOGO_URI__` filled by the build).
- `build/logo-gold.svg` — real GoldRock crest, inlined as a data URI.
- `index.html` — the built, shippable single file.
- `build-meta.json` — last build status, as-of dates, live-at-build spot.
