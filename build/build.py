#!/usr/bin/env python3
"""GoldRock Metal Exchange — historic + live price chart build pipeline.

Assembles a single self-contained index.html holding REAL daily price history
for Gold, Silver and Platinum, anchored to today's live spot, plus an
ultra-long monthly tail so the MAX view reaches back ~a century. No paid /
keyed API is used anywhere — every source below is a public, keyless endpoint.

Sources (all keyless):
  - goldprice.org  GetDataHistorical  -> real DAILY gold + silver (1973 / 1975 -> today)
  - macrotrends.net /economic-data/2540/D -> real DAILY platinum (1969 -> today)
  - macrotrends.net /economic-data/1333|1470/D -> MONTHLY gold + silver back to 1915
                                                  (spliced in before the daily era)
  - finance.yahoo.com chart API -> same-day closes to fill goldprice.org's ~1-day lag
                                   (works from cloud IPs; often 429 from residential)
  - bank.gov.ua (National Bank of Ukraine) -> official XAU/XAG/XPT reference rates,
                                   UAH/oz -> USD/oz, fills recent gaps from anywhere
  - recent.json -> our own recorded live snapshots, replayed for any day still missing
  - api.gold-api.com/price/{XAU,XAG,XPT} -> live spot, used to freshen today's tip

The browser page ALSO re-fetches api.gold-api.com live on load (it sends
Access-Control-Allow-Origin: *), so a visitor always sees current spot even
between builds. This script keeps the baked baseline fresh and is meant to run
twice daily from launchd (see ../launchd/*.plist).

Writes atomically: builds into a temp file and swaps in only on success, so a
failed fetch can never replace a good index.html with a broken one.

Run manually:  python3 build.py
"""
import json, re, sys, os, math, datetime, traceback, urllib.request
from zoneinfo import ZoneInfo

NY = ZoneInfo('America/New_York')
UTC = datetime.timezone.utc
BUILD_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BUILD_DIR)
# OUT_DIR override lets CI (GitHub Actions) publish into a Pages folder; default = local project.
OUT_DIR = os.environ.get('GOLDROCK_OUT_DIR', PROJECT_DIR)
# GOLDROCK_TEMPLATE / GOLDROCK_INDEX let a second (experimental) template build to its
# own output alongside the canonical one. Defaults preserve the original pipeline exactly.
TEMPLATE_NAME = os.environ.get('GOLDROCK_TEMPLATE', 'template.html')
INDEX_NAME = os.environ.get('GOLDROCK_INDEX', 'index.html')
LOGO_NAME = os.environ.get('GOLDROCK_LOGO', 'logo-gold.svg')
CANONICAL_OUT = os.path.join(OUT_DIR, INDEX_NAME)
MIRROR_OUT = '/tmp/goldrock-metals-chart/' + INDEX_NAME
# Persisted per-day price snapshots — fills days the free source lags on so the
# chart never shows a gap for a recent trading day (see load/save/splice_recent).
RECENT_PATH = os.path.join(PROJECT_DIR, 'recent.json')
LOG_PATH = os.path.expanduser('~/Library/Logs/goldrock-metals-chart.log')
EPOCH = datetime.date(1970, 1, 1)
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
GOLDPRICE_HEADERS = {'User-Agent': UA, 'Referer': 'https://goldprice.org/'}


def log(msg):
    line = '[{}] {}'.format(datetime.datetime.now(UTC).isoformat(timespec='seconds'), msg)
    print(line, flush=True)
    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, 'a') as f:
            f.write(line + '\n')
    except OSError:
        pass


def fetch(url, headers=None, timeout=30, tries=2):
    """GET with one retry — a transient blip in a scheduled CI run shouldn't kill the refresh."""
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=headers or {'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode('utf-8', 'replace')
        except Exception as e:
            last = e
            if attempt + 1 < tries:
                import time
                time.sleep(3)
    raise last


def fetch_json(url, headers=None, timeout=30):
    return json.loads(fetch(url, headers, timeout))


def day_offset(d):
    """days since 1970-01-01 for a datetime.date."""
    return (d - EPOCH).days


def iso_to_offset(iso):
    y, m, dd = map(int, iso.split('-'))
    return day_offset(datetime.date(y, m, dd))


# ---------------------------------------------------------------- goldprice.org
def parse_goldprice_raw(text):
    """goldprice.org returns e.g. ["USD-XAU!,<off>,<price>,<off>,<price>,..."]
    where <off> is (unix_seconds / 100). Returns list of (unix_seconds, price)."""
    txt = text.strip().strip('[]"')
    parts = txt.split(',')[1:]  # drop the "USD-XAU!" label
    pts = []
    for i in range(0, len(parts) - 1, 2):
        try:
            off = float(parts[i]); price = float(parts[i + 1])
        except ValueError:
            continue
        if price > 0:
            pts.append((off * 100.0, price))
    return pts


def to_daily(pts):
    """Collapse intraday points to one (date, price) per UTC calendar day,
    keeping the last price seen for that day. Returns [(iso_date, price), ...]."""
    by_day, order = {}, []
    for ts, price in pts:
        key = datetime.datetime.fromtimestamp(ts, tz=UTC).date().isoformat()
        if key not in by_day:
            order.append(key)
        by_day[key] = price
    return [(k, by_day[k]) for k in order]


def fetch_goldprice_daily(sym):
    raw = fetch('https://data-asg.goldprice.org/GetDataHistorical/USD-%s/0' % sym,
                GOLDPRICE_HEADERS)
    return to_daily(parse_goldprice_raw(raw))


# ---------------------------------------------------------------- macrotrends
def fetch_macrotrends(pid):
    """macrotrends /economic-data/<pid>/D -> {"data":[[ms_epoch, price], ...]}.
    Returns [(iso_date, price), ...]."""
    url = 'https://www.macrotrends.net/economic-data/%s/D' % pid
    headers = {'User-Agent': UA,
               'Referer': 'https://www.macrotrends.net/%s/x' % pid,
               'X-Requested-With': 'XMLHttpRequest'}
    j = fetch_json(url, headers)
    out = []
    for ms, price in j['data']:
        try:
            p = float(price)
        except (TypeError, ValueError):
            continue
        if p <= 0:
            continue
        d = datetime.datetime.fromtimestamp(ms / 1000.0, tz=UTC).date()
        out.append((d.isoformat(), p))
    return out


# ---------------------------------------------------------------- assembly
def splice_long_tail(daily, monthly):
    """Prepend the monthly points that predate the daily series so the MAX view
    reaches back to the monthly source's start (~1915), then continue with the
    real daily series. `monthly` and `daily` are both [(iso, price), ...]."""
    if not daily:
        return monthly
    first_daily = daily[0][0]
    pre = [(d, p) for d, p in monthly if d < first_daily]
    return pre + daily


def merge_live_tail(daily, live_price, today_key):
    """Anchor the newest point to live spot. If today's trading date is already
    in the history, overwrite it; if it's a fresh weekday not yet published,
    append it. Never invents a new point on a weekend."""
    if not daily or live_price is None:
        return daily
    last_key, _ = daily[-1]
    if last_key == today_key:
        daily[-1] = (last_key, live_price)
    elif today_key > last_key:
        is_weekend = datetime.date.fromisoformat(today_key).weekday() >= 5
        gap = (datetime.date.fromisoformat(today_key) - datetime.date.fromisoformat(last_key)).days
        if not is_weekend and gap <= 8:
            daily.append((today_key, live_price))
        else:
            daily[-1] = (last_key, live_price)
    return daily


def fetch_yahoo_daily(sym):
    """Best-effort daily closes from Yahoo (has same-day data, unlike goldprice.org's
    ~1-day lag). Works from most cloud IPs; may be rate-limited (HTTP 429) from
    residential/datacenter IPs — failure is non-fatal. Returns [(iso, close), ...]."""
    import http.cookiejar
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    hdr = {'User-Agent': UA, 'Accept': 'application/json,text/plain,*/*'}

    def og(u):
        return op.open(urllib.request.Request(u, headers=hdr), timeout=20).read().decode('utf-8', 'replace')

    try:
        og('https://finance.yahoo.com/quote/' + sym)   # seed consent cookie
    except Exception:
        pass
    crumb = ''
    for host in ('query1.finance.yahoo.com', 'query2.finance.yahoo.com'):
        try:
            crumb = og('https://%s/v1/test/getcrumb' % host).strip(); break
        except Exception:
            continue
    for host in ('query1.finance.yahoo.com', 'query2.finance.yahoo.com'):
        try:
            u = ('https://%s/v8/finance/chart/%s?range=1mo&interval=1d' % (host, sym)
                 + ('&crumb=' + crumb if crumb else ''))
            j = json.loads(og(u))
            res = j['chart']['result'][0]
            ts = res['timestamp']; cl = res['indicators']['quote'][0]['close']
            return [(datetime.datetime.fromtimestamp(t, tz=UTC).date().isoformat(), float(c))
                    for t, c in zip(ts, cl) if c]
        except Exception:
            continue
    return []


def fill_from_yahoo(daily, ysym):
    """Append recent trading days that goldprice.org hasn't published yet, using
    Yahoo's same-day daily closes. No-op if Yahoo is unavailable."""
    yd = fetch_yahoo_daily(ysym)
    if not yd or not daily:
        return daily, 0
    have = {d for d, _ in daily}
    today_utc = datetime.datetime.now(UTC).date().isoformat()
    last = daily[-1][0]; added = 0
    for d, c in yd:
        # skip Yahoo's current-day bar — it's an in-progress price, not a close
        # (today's tip is anchored to live spot in merge_live_tail instead)
        if d >= today_utc:
            continue
        if d > last and d not in have and datetime.date.fromisoformat(d).weekday() < 5:
            daily.append((d, round(c, 2))); added += 1
    daily.sort(key=lambda x: x[0])
    return daily, added


NBU_CC = {'gold': 'XAU', 'silver': 'XAG', 'platinum': 'XPT'}


def nbu_rate(ymd, cc):
    """One NBU investment-metal / currency rate (UAH per oz, or UAH per unit).
    Short timeout, single try — this is a best-effort gap filler, never worth stalling a build."""
    j = json.loads(fetch('https://bank.gov.ua/NBU_Exchange/exchange_site?json&date=%s&valcode=%s' % (ymd, cc),
                         timeout=12, tries=1))
    return float(j[0]['rate']) if j else None


def _next_trading_day(d):
    d = d + datetime.timedelta(days=1)
    while d.weekday() >= 5:
        d += datetime.timedelta(days=1)
    return d


def fill_from_nbu(daily, metal, today_key):
    """Fill recent trading days goldprice.org hasn't published yet from the National
    Bank of Ukraine's keyless investment-metal feed (UAH/oz -> USD/oz via NBU's own
    USD rate). NBU's value is effective the next business day, so NBU date N reflects
    the market's previous trading day. Tracks London spot within ~$10. Best-effort."""
    if not daily:
        return daily, 0
    cc = NBU_CC.get(metal)
    if not cc:
        return daily, 0
    have = {d for d, _ in daily}
    last = datetime.date.fromisoformat(daily[-1][0])
    today = datetime.date.fromisoformat(today_key)
    added = 0
    # cap the window: with a months-stale tail (e.g. a last-good fallback) an unbounded
    # walk against a slow NBU could stall a scheduled run for hours
    m = max(last + datetime.timedelta(days=1), today - datetime.timedelta(days=21))
    fails = 0
    while m < today and fails < 5:                     # up to yesterday; today comes from live spot
        if m.weekday() < 5 and m.isoformat() not in have:
            nd = _next_trading_day(m)                  # NBU date whose value reflects market day m
            if nd <= today:
                try:
                    metal_uah = nbu_rate(nd.strftime('%Y%m%d'), cc)
                    usd_uah = nbu_rate(nd.strftime('%Y%m%d'), 'USD')
                    if metal_uah and usd_uah:
                        daily.append((m.isoformat(), round(metal_uah / usd_uah, 2)))
                        added += 1
                        fails = 0
                    else:
                        fails += 1
                except Exception:
                    fails += 1
        m += datetime.timedelta(days=1)
    daily.sort(key=lambda x: x[0])
    return daily, added


LASTGOOD_PATH = os.path.join(PROJECT_DIR, 'series-lastgood.json')


def fetch_cpi():
    """Annual-average CPI-U back to 1913, keyless (usinflationcalculator's BLS mirror).
    The current partial year uses its latest monthly value. Returns {year:int -> cpi:float}
    or None — the chart simply hides the Real-$ toggle rather than show wrong numbers."""
    try:
        h = fetch('https://www.usinflationcalculator.com/inflation/'
                  'consumer-price-index-and-annual-percent-changes-from-1913-to-2008/',
                  {'User-Agent': UA})
        out = {}
        for m in re.finditer(r'<strong>\s*((?:19|20)\d{2})\s*</strong>\s*</td>(.*?)</tr>', h, re.S):
            year = int(m.group(1))
            vals = re.findall(r'<td[^>]*>\s*([\d.]+)\s*</td>', m.group(2))
            if len(vals) >= 13:
                out[year] = float(vals[12])       # 13th numeric cell = annual average
            elif vals:
                out[year] = float(vals[-1])       # partial current year: latest month
        if len(out) >= 100:
            return out
        log('WARN cpi parse found only %d years' % len(out))
    except Exception as e:
        log('WARN cpi fetch failed: %s' % e)
    return None


def ordinal(n):
    return '%d%s' % (n, 'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th'))


def market_note(daily):
    """One factual sentence about gold, composed purely from the data — no opinions,
    no advice, refreshed with every build."""
    try:
        if len(daily) < 4:
            return ''
        cur = daily[-1][1]; prev = daily[-2][1]
        chg = cur - prev
        pct = chg / prev * 100 if prev else 0
        up = chg >= 0
        streak = 1
        for i in range(len(daily) - 1, 1, -1):
            if ((daily[i - 1][1] - daily[i - 2][1]) >= 0) == up:
                streak += 1
                if streak >= 9:
                    break
            else:
                break
        ath = max(p for _, p in daily)
        note = 'Gold is at $%s, %s %.1f%% from the prior close' % (
            format(cur, ',.2f'), 'up' if up else 'down', abs(pct))
        if streak >= 3:
            note += ' — its %s consecutive %s' % (ordinal(streak), 'gain' if up else 'decline')
        gap = (1 - cur / ath) * 100
        if cur >= ath:
            note += ' — a new all-time high'
        elif gap <= 5:
            note += ', %.1f%% below the all-time high' % gap
        return note + '.'
    except Exception:
        return ''


def load_lastgood_key(key):
    try:
        with open(LASTGOOD_PATH) as f:
            return json.load(f).get(key)
    except Exception:
        return None


def save_lastgood(gold, silver, platinum, cpi=None):
    """Persist the fully-assembled daily series so a future run whose SOURCE dies can
    still publish (frozen history + live tip) instead of failing until the source heals.
    Written atomically — a truncate-then-crash must never destroy the only fallback."""
    try:
        tmp = LASTGOOD_PATH + '.tmp'
        with open(tmp, 'w') as f:
            json.dump({'gold': gold, 'silver': silver, 'platinum': platinum, 'cpi': cpi}, f)
        os.replace(tmp, LASTGOOD_PATH)
    except OSError as e:
        log('WARN could not save series-lastgood.json: %s' % e)


def load_lastgood(metal):
    try:
        with open(LASTGOOD_PATH) as f:
            return [(d, p) for d, p in json.load(f)[metal]]
    except Exception:
        return []


def load_recent():
    try:
        with open(RECENT_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def save_recent(rec):
    keys = sorted(rec)[-70:]                      # keep ~10 weeks of snapshots
    rec = {k: rec[k] for k in keys}
    try:
        tmp = RECENT_PATH + '.tmp'
        with open(tmp, 'w') as f:
            json.dump(rec, f)
        os.replace(tmp, RECENT_PATH)
    except OSError:
        pass


def splice_recent(daily, metal, rec):
    """Append recorded daily snapshots (captured live on prior builds) for any
    trading day newer than the source's last published date. This closes the
    1-2 day gap the free feed leaves before it publishes a session's close."""
    if not daily:
        return daily
    last = daily[-1][0]
    for d in sorted(rec):
        v = rec.get(d, {}).get(metal)
        if d > last and v and datetime.date.fromisoformat(d).weekday() < 5:
            daily.append((d, float(v)))
            last = d
    return daily


def thin(daily, weekly_before='2006-01-01'):
    """Keep full daily resolution for the last ~20 years (what visitors zoom
    into) and collapse older history to one point per ISO week. Cuts file size
    ~2x with no visible loss when zoomed out. Always keeps the first & last."""
    if not daily:
        return daily
    out, seen_week = [], set()
    for i, (iso, price) in enumerate(daily):
        if iso >= weekly_before or i == 0 or i == len(daily) - 1:
            out.append((iso, price))
            continue
        y, m, d = map(int, iso.split('-'))
        wk = datetime.date(y, m, d).isocalendar()[:2]  # (iso_year, iso_week)
        if wk not in seen_week:
            seen_week.add(wk)
            out.append((iso, price))
    return out


def round_price(p):
    if p >= 100:
        return round(p, 1)
    if p >= 10:
        return round(p, 2)
    return round(p, 3)


def encode(daily):
    return [[iso_to_offset(iso), round_price(p)] for iso, p in daily]


def run():
    log('build started')
    # UTC, to match how every source keys its days — an NY date would lag UTC by one
    # day between 8pm ET and midnight ET and misfile evening builds.
    today_key = datetime.datetime.now(UTC).strftime('%Y-%m-%d')

    # --- live spot (keyless, also used by the browser on load) ---
    live = {}
    for key, sym in (('gold', 'XAU'), ('silver', 'XAG'), ('platinum', 'XPT')):
        try:
            live[key] = float(fetch_json('https://api.gold-api.com/price/' + sym)['price'])
        except Exception as e:
            live[key] = None
            log('WARN live %s failed: %s' % (key, e))
    log('live spot: %s' % live)

    # --- real daily history, with a last-good fallback per metal: a dead or gutted feed
    # (format change, error page, truncation) degrades to "frozen history + live tip"
    # instead of killing every future build until the source heals ---
    def hist(name, metal, fn, *args):
        try:
            s = fn(*args)
            if len(s) >= 5000:
                return s
            log('WARN %s returned only %d points — falling back to last good' % (name, len(s)))
        except Exception as e:
            log('WARN %s history fetch failed (%s) — falling back to last good' % (name, e))
        lg = load_lastgood(metal)
        if len(lg) >= 5000:
            log('using last-good %s series (%d points, through %s)' % (metal, len(lg), lg[-1][0]))
            return lg
        raise RuntimeError('%s failed and no last-good series is available — refusing to publish' % name)

    gold_daily = hist('goldprice gold', 'gold', fetch_goldprice_daily, 'XAU')
    silver_daily = hist('goldprice silver', 'silver', fetch_goldprice_daily, 'XAG')
    platinum_daily = hist('macrotrends platinum', 'platinum', fetch_macrotrends, 2540)
    log('daily raw: gold=%d(%s..%s) silver=%d(%s..%s) platinum=%d(%s..%s)' % (
        len(gold_daily), gold_daily[0][0], gold_daily[-1][0],
        len(silver_daily), silver_daily[0][0], silver_daily[-1][0],
        len(platinum_daily), platinum_daily[0][0], platinum_daily[-1][0]))

    # --- splice ultra-long monthly tail (gold/silver back to ~1915) ---
    try:
        gold_daily = splice_long_tail(gold_daily, fetch_macrotrends(1333))
        silver_daily = splice_long_tail(silver_daily, fetch_macrotrends(1470))
        log('spliced long tail: gold from %s, silver from %s' % (gold_daily[0][0], silver_daily[0][0]))
    except Exception as e:
        log('WARN long tail splice failed (keeping daily-only): %s' % e)

    # --- fill days goldprice.org hasn't published yet (Yahoo works from cloud IPs;
    #     NBU official feed works everywhere incl. this Mac) ---
    try:
        gold_daily, ng = fill_from_yahoo(gold_daily, 'XAUUSD=X')
        silver_daily, ns = fill_from_yahoo(silver_daily, 'XAGUSD=X')
        log('yahoo fill: gold +%d silver +%d' % (ng, ns))
    except Exception as e:
        log('WARN yahoo fill failed: %s' % e)
    try:
        gold_daily, ng2 = fill_from_nbu(gold_daily, 'gold', today_key)
        silver_daily, ns2 = fill_from_nbu(silver_daily, 'silver', today_key)
        platinum_daily, np2 = fill_from_nbu(platinum_daily, 'platinum', today_key)
        log('nbu fill: gold +%d silver +%d platinum +%d' % (ng2, ns2, np2))
    except Exception as e:
        log('WARN nbu fill failed: %s' % e)

    # --- record today's live into the snapshot store, then fill any days the
    #     source lags on from previously-recorded snapshots (no more gaps) ---
    recent = load_recent()
    if datetime.date.fromisoformat(today_key).weekday() < 5:
        recent.setdefault(today_key, {})
        for k in ('gold', 'silver', 'platinum'):
            if live.get(k):
                recent[today_key][k] = round(live[k], 4)
    gold_daily = splice_recent(gold_daily, 'gold', recent)
    silver_daily = splice_recent(silver_daily, 'silver', recent)
    platinum_daily = splice_recent(platinum_daily, 'platinum', recent)
    save_recent(recent)
    log('recent snapshots: %d days; tails now gold..%s silver..%s platinum..%s' % (
        len(recent), gold_daily[-1][0], silver_daily[-1][0], platinum_daily[-1][0]))

    # --- anchor today's tip to live spot ---
    gold_daily = merge_live_tail(gold_daily, live['gold'], today_key)
    silver_daily = merge_live_tail(silver_daily, live['silver'], today_key)
    platinum_daily = merge_live_tail(platinum_daily, live['platinum'], today_key)

    # --- annual CPI for the Real-$ (inflation-adjusted) view ---
    cpi = fetch_cpi()
    if not cpi:
        lg = load_lastgood_key('cpi')
        if lg:
            cpi = {int(k): v for k, v in lg.items()}
            log('using last-good CPI (%d years)' % len(cpi))
    log('cpi: %s' % ('%d years, latest %s=%s' % (len(cpi), max(cpi), cpi[max(cpi)]) if cpi else 'unavailable — Real-$ toggle hidden'))

    # --- remember this fully-assembled state for future fallback runs ---
    save_lastgood(gold_daily, silver_daily, platinum_daily, cpi)

    # --- thin old history, encode compactly ---
    series = {
        'gold': encode(thin(gold_daily)),
        'silver': encode(thin(silver_daily)),
        'platinum': encode(thin(platinum_daily)),
    }

    # fall back to the last baked-in tip if a live fetch failed
    for k, d in (('gold', gold_daily), ('silver', silver_daily), ('platinum', platinum_daily)):
        if live.get(k) is None and d:
            live[k] = d[-1][1]

    meta = {
        'built_utc': datetime.datetime.now(UTC).isoformat(timespec='seconds'),
        'built_ny': datetime.datetime.now(NY).strftime('%b %-d, %Y %-I:%M %p ET'),
        'asof': {'gold': gold_daily[-1][0], 'silver': silver_daily[-1][0], 'platinum': platinum_daily[-1][0]},
        'start': {'gold': gold_daily[0][0], 'silver': silver_daily[0][0], 'platinum': platinum_daily[0][0]},
        'live': {k: round(v, 2) if v else v for k, v in live.items()},
        'points': {k: len(v) for k, v in series.items()},
        'note': market_note(gold_daily),
        'cpi': {str(k): v for k, v in sorted(cpi.items())} if cpi else None,
        'cpiBase': cpi[max(cpi)] if cpi else None,
    }

    data_json = json.dumps(series, separators=(',', ':'))
    meta_json = json.dumps(meta, separators=(',', ':'))

    with open(os.path.join(BUILD_DIR, TEMPLATE_NAME)) as f:
        tpl = f.read()
    import base64
    with open(os.path.join(BUILD_DIR, LOGO_NAME), 'rb') as f:
        logo_uri = 'data:image/svg+xml;base64,' + base64.b64encode(f.read()).decode('ascii')
    with open(os.path.join(BUILD_DIR, 'hero.jpg'), 'rb') as f:
        hero_uri = 'data:image/jpeg;base64,' + base64.b64encode(f.read()).decode('ascii')
    final = (tpl.replace('/*__DATA_JSON__*/0', data_json)
                .replace('/*__META_JSON__*/0', meta_json)
                .replace('__LOGO_URI__', logo_uri)
                .replace('__HERO_URI__', hero_uri))

    for out in (CANONICAL_OUT, MIRROR_OUT):
        try:
            os.makedirs(os.path.dirname(out), exist_ok=True)
            tmp = out + '.tmp'
            with open(tmp, 'w') as f:
                f.write(final)
            os.replace(tmp, out)
            log('wrote %s (%d bytes)' % (out, len(final)))
        except OSError as e:
            log('WARN could not write %s: %s' % (out, e))

    for meta_dir in {PROJECT_DIR, OUT_DIR}:          # OUT_DIR copy ships with the Pages artifact
        try:
            with open(os.path.join(meta_dir, 'build-meta.json'), 'w') as f:
                json.dump(meta, f, indent=2)
        except OSError as e:
            log('WARN could not write build-meta.json to %s: %s' % (meta_dir, e))
    log('build ok — points %s' % meta['points'])


if __name__ == '__main__':
    try:
        run()
    except Exception:
        log('BUILD FAILED:\n' + traceback.format_exc())
        sys.exit(1)
