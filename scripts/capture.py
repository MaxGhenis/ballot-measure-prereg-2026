"""Capture the study's raw data into one stamped directory, with a manifest. Nothing here transforms data; panel.py and
run_analysis.py do that.

  python scripts/capture.py all                 every registered asset and market (the runbook's capture command)
  python scripts/capture.py assets [TICKERS]    Yahoo chart service; default: every ticker and benchmark in registry/assets.csv
                                                plus VTEB and TFI. Daily (2y, adjusted), 60-minute (730d), 5-minute (60d).
  python scripts/capture.py markets             every market in registry/markets.csv: Kalshi 60-minute candlesticks over the
                                                market's life and 1-minute candlesticks from October 20, 2026
                                                (live endpoint, then the historical endpoint) and the market record (status,
                                                result, close and settlement times); Polymarket CLOB price history for the Yes token
                                                (60-minute over its life, 1-minute from October 20) and the Gamma market record (closed, outcome prices).
  --dir DIR                                     write into DIR instead of a new data/raw/capture/<UTC stamp>/.

Every request outcome goes to manifest.json in the directory: files written (bytes, sha256) and failures (URL, error). A
market whose candle endpoints both fail is recorded as a failure and no file is written for it. Yahoo keeps 5-minute bars
for about 60 days and 60-minute bars for about 730 days."""
import csv, datetime as dt, hashlib, json, pathlib, sys, time, urllib.parse, urllib.request
ROOT = pathlib.Path(__file__).resolve().parents[1]
STAMP = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
OUT = ROOT / "data/raw/capture" / STAMP
UA = {"User-Agent": "Mozilla/5.0 (research; max@logpile.ai)"}
EXTRA_TICKERS = ["VTEB", "TFI"]
MINUTE_FROM = int(dt.datetime(2026, 10, 20, tzinfo=dt.timezone.utc).timestamp())   # start of 1-minute market data
MANIFEST = {"stamp": STAMP, "started": None, "finished": None, "files": {}, "failures": [], "commands": []}


def get(url, tries=4):
    err = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r: return json.load(r)
        except Exception as e:
            err = e; time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"{url}: {err}")


def save(name, obj):
    OUT.mkdir(parents=True, exist_ok=True)
    b = json.dumps({"retrieved": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "data": obj}).encode()
    (OUT / name).write_bytes(b)
    MANIFEST["files"][name] = {"bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()}


def fail(what, err):
    MANIFEST["failures"].append({"what": what, "error": str(err)[:500]})
    print("ERR", what, err, file=sys.stderr, flush=True)


def write_manifest():
    OUT.mkdir(parents=True, exist_ok=True)
    MANIFEST["finished"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    (OUT / "manifest.json").write_text(json.dumps(MANIFEST, indent=1))


def registry_tickers():
    ts = []
    for a in csv.DictReader(open(ROOT / "registry/assets.csv")):
        if a.get("rank") == "1":
            ts += [t for t in a["tickers"].split(";") + a["benchmark"].split(";") if t]
    return list(dict.fromkeys(ts + EXTRA_TICKERS))


def assets(tickers):
    Y = "https://query1.finance.yahoo.com/v8/finance/chart/"
    for t in tickers or registry_tickers():
        for rng, iv in (("2y", "1d"), ("730d", "60m"), ("60d", "5m")):
            url = Y + t + "?" + urllib.parse.urlencode({"range": rng, "interval": iv, "includeAdjustedClose": "true"})
            try:
                d = get(url)
                res = (d.get("chart") or {}).get("result") or []
                if not res or not res[0].get("timestamp"):
                    fail(f"yahoo {t} {iv}", "empty result"); continue
                save(f"yahoo_{t}_{iv}.json", d)
            except RuntimeError as e:
                fail(f"yahoo {t} {iv}", e)
            time.sleep(0.3)
        print("asset", t, flush=True)


K = "https://api.elections.kalshi.com/trade-api/v2"


def kalshi_market(series, ticker, open_time, close_time):
    for path in (f"/markets/{ticker}", f"/historical/markets/{ticker}"):
        try:
            save(f"kalshi_{ticker}_market.json", get(K + path, tries=2)); break
        except RuntimeError as e:
            last = e
    else:
        fail(f"kalshi market record {ticker}", last)
    ts = lambda s: int(dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())
    start, end = ts(open_time) - 3600, min(ts(close_time) + 86400, int(time.time()))
    for interval in (1, 60):
        lo = max(start, MINUTE_FROM) if interval == 1 else start     # 1-minute candles only from MINUTE_FROM (the W3 window)
        if lo >= end:
            MANIFEST.setdefault("skipped", []).append(f"kalshi candles {ticker} {interval}m: window starts after now"); continue
        got, errs = None, []
        for path in (f"/series/{series}/markets/{ticker}/candlesticks", f"/historical/markets/{ticker}/candlesticks"):
            step = interval * 60 * 4000; out = []
            try:
                for a in range(lo, end, step):
                    d = get(K + path + "?" + urllib.parse.urlencode({"start_ts": a, "end_ts": min(a + step, end), "period_interval": interval}))
                    out += d.get("candlesticks") or []; time.sleep(0.25)
                got = out; break
            except RuntimeError as e:
                errs.append(str(e))
        if got is None: fail(f"kalshi candles {ticker} {interval}m", " | ".join(errs))
        elif not got: fail(f"kalshi candles {ticker} {interval}m", "endpoint returned no candles")
        else: save(f"kalshi_{ticker}_{interval}m.json", got)


def polymarket(market_id, token, start_ts):
    """The CLOB refuses start-to-end ranges longer than about 14 days, so: the whole life at 60-minute fidelity
    (interval=max), and 1-minute fidelity from MINUTE_FROM in 7-day chunks."""
    CL = "https://clob.polymarket.com/prices-history?"
    try: save(f"pm_market_{market_id}.json", get(f"https://gamma-api.polymarket.com/markets/{market_id}"))
    except RuntimeError as e: fail(f"polymarket market record {market_id}", e)
    try:
        d = get(CL + urllib.parse.urlencode({"market": token, "interval": "max", "fidelity": 60}))
        if not (d.get("history") or []): fail(f"polymarket history {token} 60m", "empty history")
        else: save(f"pm_{token}_60m.json", d)
    except RuntimeError as e:
        fail(f"polymarket history {token} 60m", e)
    hist, now, a = [], int(time.time()), max(start_ts, MINUTE_FROM)
    if a >= now:
        MANIFEST.setdefault("skipped", []).append(f"polymarket history {token} 1m: window starts after now"); return
    try:
        while a < now:
            b = min(a + 7 * 86400, now)
            hist += get(CL + urllib.parse.urlencode({"market": token, "startTs": a, "endTs": b, "fidelity": 1})).get("history") or []
            a = b; time.sleep(0.2)
        if hist: save(f"pm_{token}_1m.json", {"history": sorted({h["t"]: h for h in hist}.values(), key=lambda h: h["t"])})
    except RuntimeError as e:
        fail(f"polymarket history {token} 1m", e)


def markets():
    for r in csv.DictReader(open(ROOT / "registry/markets.csv")):
        if r["venue"] == "kalshi":
            kalshi_market(r["series"], r["market"], r["open_time"], r["close_time"])
        else:
            toks = json.loads(r["clob_token_ids"] or "[]")
            if not toks: fail(f"polymarket {r['market']}", "no CLOB token in registry"); continue
            polymarket(r["market"], toks[0], int(dt.datetime.fromisoformat(r["open_time"].replace("Z", "+00:00")).timestamp()))
        print("market", r["venue"], r["market"], flush=True)


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--dir" in args:
        i = args.index("--dir"); OUT = pathlib.Path(args[i + 1]).resolve(); MANIFEST["stamp"] = OUT.name; del args[i:i + 2]
    if not args or args[0] not in ("all", "assets", "markets"):
        sys.exit(__doc__)
    if (OUT / "manifest.json").exists():
        MANIFEST.update(json.load(open(OUT / "manifest.json")))
    MANIFEST["started"] = MANIFEST["started"] or dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    MANIFEST["commands"].append(" ".join(sys.argv))
    try:
        if args[0] in ("all", "assets"): assets(args[1:] if args[0] == "assets" else [])
        if args[0] in ("all", "markets"): markets()
    finally:
        write_manifest()
    print("wrote", OUT, "files:", len(MANIFEST["files"]), "failures:", len(MANIFEST["failures"]))
