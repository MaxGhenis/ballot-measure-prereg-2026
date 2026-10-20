"""Coverage check for the Polymarket side of the enumeration. Gamma refuses offsets past about 2,000, so paging every open
event (scripts/enumerate_markets.py) can stop before the end of the list. This sweep pages open events by end date
instead, from November 2, 2026 to January 31, 2027, halving any window that reaches the cap until every window is read in
full, and lists every market whose event title or question names a U.S. state or large city together with a ballot-measure
keyword. It reports each such market that the enumeration (data/derived/markets_polymarket.csv) did not keep.

Writes data/derived/polymarket_end_date_sweep.json (windows, event counts, hits, misses, retrieval time)."""
import csv, datetime as dt, json, pathlib, re, time, urllib.parse, urllib.request
ROOT = pathlib.Path(__file__).resolve().parents[1]
UA = {"User-Agent": "research (max@logpile.ai)"}
PLACES = re.compile(r"Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|Florida|Georgia|Hawaii|Idaho|"
                    r"Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|Massachusetts|Michigan|Minnesota|"
                    r"Mississippi|Missouri|Montana|Nebraska|Nevada|New Hampshire|New Jersey|New Mexico|New York|North Carolina|"
                    r"North Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|South Carolina|South Dakota|Tennessee|Texas|"
                    r"Utah|Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming|NYC|San Francisco|Los Angeles|Denver|"
                    r"Seattle|Portland|Chicago|Honolulu|Oakland|Boston|Austin", re.I)
KW = re.compile(r"ballot measure|ballot initiative|proposition|\bprop\b|amendment|initiative|\bquestion\b|referendum|"
                r"\bmeasure\b|charter|bond|tax|issue \d", re.I)


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r: return json.load(r)


def sweep(lo, hi, out, depth=0):
    off, n, hits, capped = 0, 0, [], False
    while True:
        q = {"closed": "false", "limit": 100, "offset": off, "end_date_min": lo.isoformat() + "Z", "end_date_max": hi.isoformat() + "Z"}
        try: page = get("https://gamma-api.polymarket.com/events?" + urllib.parse.urlencode(q))
        except Exception as e:
            capped = True; err = str(e); break
        if not page: break
        n += len(page); off += 100; time.sleep(0.15)
        for e in page:
            for m in e.get("markets") or []:
                txt = f"{e.get('title', '')} | {m.get('question', '')}"
                if KW.search(txt) and PLACES.search(txt): hits.append({"market": str(m.get("id")), "text": txt[:200]})
    if capped and depth < 8:
        mid = lo + (hi - lo) / 2
        return sweep(lo, mid, out, depth + 1) + sweep(mid, hi, out, depth + 1)
    out.append({"from": lo.isoformat() + "Z", "to": hi.isoformat() + "Z", "events": n, "read_in_full": not capped, **({"error": err} if capped else {})})
    return hits


if __name__ == "__main__":
    windows = []
    got = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    hits = []
    for lo, hi in ((dt.datetime(2026, 11, 2), dt.datetime(2026, 12, 1)), (dt.datetime(2026, 12, 1), dt.datetime(2027, 1, 31, 23, 59, 59))):
        hits += sweep(lo, hi, windows)
    kept = {r["market"] for r in csv.DictReader(open(ROOT / "data/derived/markets_polymarket.csv"))}
    uniq = {h["market"]: h for h in hits}
    miss = [h for m, h in sorted(uniq.items()) if m not in kept]
    res = {"retrieved": got, "windows": windows, "all_windows_read_in_full": all(w["read_in_full"] for w in windows),
           "hits": len(uniq), "not_in_enumeration": miss}
    (ROOT / "data/derived/polymarket_end_date_sweep.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({k: res[k] for k in ("retrieved", "all_windows_read_in_full", "hits", "not_in_enumeration")}, indent=1))
    for w in windows: print(w)
