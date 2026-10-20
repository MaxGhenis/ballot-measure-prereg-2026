"""Enumerate every Kalshi and Polymarket market on a U.S. state or local ballot measure decided on November 3, 2026.

Kalshi (public trade API v2, no auth): all series; candidates are Elections/Politics series whose title or ticker names a
ballot measure, proposition, amendment, initiative, question, referendum or measure-like tax; every market in a candidate
series is fetched with its order-book quote and rules, and kept if it is open or closes on/after 2026-11-03.
Polymarket (Gamma API, no auth): every open event, paged; kept if its title or a market question names a U.S. ballot measure.
Writes raw JSON under data/raw/ and data/derived/markets_{kalshi,polymarket}.csv. Retrieval time is recorded in each file."""
import csv, datetime as dt, json, pathlib, re, sys, time, urllib.parse, urllib.request
ROOT = pathlib.Path(__file__).resolve().parents[1]; RAW = ROOT / "data/raw"; DER = ROOT / "data/derived"
RAW.mkdir(parents=True, exist_ok=True); DER.mkdir(parents=True, exist_ok=True)
NOW = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
UA = {"User-Agent": "research (max@logpile.ai)"}
REQUEST_LOG = []   # every request that failed after retries; a non-empty log marks the enumeration incomplete
OFFSET_CAP = []    # Gamma pagings stopped at the API's 2,000-offset cap
CANDIDATES = []    # every candidate considered, with the decision and the reason
def get(url, tries=5):
    err = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r: return json.load(r)
        except Exception as e:
            err = e; time.sleep(1.5 * (i + 1))
    REQUEST_LOG.append({"url": url, "error": str(err)[:300]})
    raise RuntimeError(f"{url}: {err}")
K = "https://api.elections.kalshi.com/trade-api/v2"
STATES = ["Alabama","Alaska","Arizona","Arkansas","California","Colorado","Connecticut","Delaware","Florida","Georgia","Hawaii","Idaho","Illinois","Indiana","Iowa","Kansas","Kentucky","Louisiana","Maine","Maryland","Massachusetts","Michigan","Minnesota","Mississippi","Missouri","Montana","Nebraska","Nevada","New Hampshire","New Jersey","New Mexico","New York","North Carolina","North Dakota","Ohio","Oklahoma","Oregon","Pennsylvania","Rhode Island","South Carolina","South Dakota","Tennessee","Texas","Utah","Vermont","Virginia","Washington","West Virginia","Wisconsin","Wyoming"]
KW = re.compile(r"ballot measure|ballot initiative|proposition|\bprop\b|amendment|initiative|\bquestion\b|referendum|\bmeasure\b|charter|bond measure|tax", re.I)
FOREIGN = re.compile(r"\b(alberta|swiss|switzerland|scotland|scottish|wales|welsh|taiwan|guinea|iceland|ireland|irish|fiji|slovak\w*|italy|italian|bangladesh\w*|french|europe\w*|canad\w*|uk|brexit)\b|july charter|eu referend", re.I)
NOT_MEASURE = re.compile(r"25th amendment|22nd amendment|2nd amendment|3rd amendment|14th amendment|first amendment|constitutional amendment\b(?!.*state)|twitter files|scotus|usps|mail ballot|generic ballot|on the ballot\?$|be on .* ballot|ballot deadline|drop out|america party|house amendment|protect college sports|tariff|trump", re.I)

SNAP = ROOT.parent / "data/raw"   # the memo's October 11 Kalshi pull, used when the live API is unreachable
def kalshi_offline():
    """Fallback: the October 11, 2026 series list and market files saved by the memo. Labeled as such in every output."""
    d = json.load(open(SNAP / "kalshi_series_all.json")); series = d.get("series", d) if isinstance(d, dict) else d
    return series
def kalshi():
    global KALSHI_SOURCE
    try:
        series, cursor = [], None
        while True:
            d = get(K + "/series?" + urllib.parse.urlencode({"limit": 1000, **({"cursor": cursor} if cursor else {})}), tries=2)
            series += d.get("series") or []; cursor = d.get("cursor")
            if not cursor: break
        KALSHI_SOURCE = f"live {NOW}"
    except RuntimeError as e:
        print("Kalshi API unreachable:", e, file=sys.stderr)
        KALSHI_SOURCE = "snapshot 2026-10-11 (live API unreachable at " + NOW + ")"
        return kalshi_snapshot_rows()
    (RAW / "kalshi_series_all.json").write_text(json.dumps({"retrieved": NOW, "series": series}))
    cand = [s for s in series if s.get("category") in ("Elections", "Politics", "Economics")
            and (KW.search(s.get("title") or "") or re.search(r"BALLOT|MEASURE|PROP|AMEND|AMD|QUESTION|REFERENDUM|TAX", s["ticker"]))
            and not FOREIGN.search(s.get("title") or "")]
    for s in series:
        if s.get("category") in ("Elections", "Politics", "Economics"):
            CANDIDATES.append({"venue": "kalshi", "id": s["ticker"], "title": s.get("title"), "decision": "kept" if s in cand else "rejected", "reason": "" if s in cand else "no measure keyword or foreign"})
    rows, raw = [], {}
    for s in cand:
        mk, cursor = [], None
        while True:
            q = {"series_ticker": s["ticker"], "limit": 1000, **({"cursor": cursor} if cursor else {})}
            d = get(K + "/markets?" + urllib.parse.urlencode(q)); mk += d.get("markets") or []; cursor = d.get("cursor")
            if not cursor: break
        mk = [m for m in mk if (m.get("close_time") or "") >= "2026-11-03" and m.get("status") not in ("settled", "finalized")]
        if not mk: continue
        raw[s["ticker"]] = {"series": s, "markets": mk}
        for m in mk:
            rows.append({"venue": "kalshi", "series": s["ticker"], "series_title": s.get("title"), "event": m.get("event_ticker"),
                         "market": m["ticker"], "title": m.get("title"), "subtitle": m.get("yes_sub_title") or m.get("subtitle"),
                         "status": m.get("status"), "open_time": m.get("open_time"), "close_time": m.get("close_time"),
                         "expected_expiration": m.get("expected_expiration_time"), "volume": m.get("volume_fp") or m.get("volume"),
                         "volume_24h": m.get("volume_24h_fp") or m.get("volume_24h"), "open_interest": m.get("open_interest_fp") or m.get("open_interest"),
                         "liquidity": m.get("liquidity_dollars") or m.get("liquidity"), "yes_bid": m.get("yes_bid_dollars"), "yes_ask": m.get("yes_ask_dollars"),
                         "last": m.get("last_price_dollars"), "rules": (m.get("rules_primary") or "").replace("\n", " ")})
        time.sleep(0.2)
    (RAW / "kalshi_measure_markets.json").write_text(json.dumps({"retrieved": NOW, "series_scanned": len(series), "candidates": len(cand), "markets": raw}, indent=1))
    return rows, len(series), len(cand)

def kalshi_snapshot_rows():
    """Markets from the October 11 snapshot that close on/after Nov 3, 2026: KXSTATEBALLOTMEASURE plus one-off measure series."""
    series = kalshi_offline(); rows = []
    for f in sorted((SNAP / "kalshi").glob("markets_*.json")):
        s = f.stem.replace("markets_", ""); meta = next((x for x in series if x["ticker"] == s), {})
        for m in json.load(open(f)):
            if (m.get("close_time") or "") < "2026-11-03" or m.get("status") in ("settled", "finalized"): continue
            rows.append({"venue": "kalshi", "series": s, "series_title": meta.get("title"), "event": m.get("event_ticker"), "market": m["ticker"],
                         "title": m.get("title"), "subtitle": m.get("yes_sub_title"), "status": m.get("status"), "open_time": m.get("open_time"),
                         "close_time": m.get("close_time"), "expected_expiration": m.get("expected_expiration_time"), "volume": m.get("volume_fp"),
                         "volume_24h": m.get("volume_24h_fp"), "open_interest": m.get("open_interest_fp"), "liquidity": m.get("liquidity_dollars"),
                         "yes_bid": m.get("yes_bid_dollars"), "yes_ask": m.get("yes_ask_dollars"), "last": m.get("last_price_dollars"),
                         "rules": (m.get("rules_primary") or "").replace("\n", " ")})
    cand = [x for x in series if x.get("category") in ("Elections", "Politics", "Economics")
            and (KW.search(x.get("title") or "") or re.search(r"BALLOT|MEASURE|PROP|AMEND|AMD|QUESTION|REFERENDUM|TAX", x["ticker"]))
            and not FOREIGN.search(x.get("title") or "")]
    for x in series:
        if x.get("category") in ("Elections", "Politics", "Economics"):
            CANDIDATES.append({"venue": "kalshi (snapshot)", "id": x["ticker"], "title": x.get("title"), "decision": "kept" if x in cand else "rejected", "reason": "" if x in cand else "no measure keyword or foreign"})
    (RAW / "kalshi_candidate_series_snapshot.json").write_text(json.dumps([{k: x.get(k) for k in ("ticker", "title", "category", "frequency")} for x in cand], indent=1))
    return rows, len(series), len(cand)

KALSHI_SOURCE = None
G = "https://gamma-api.polymarket.com"
def polymarket():
    # Gamma refuses offsets past about 2,000, so page by tag and add keyword searches; dedupe by event id.
    seen = {}
    def page_events(params):
        off = 0
        while True:
            if off >= 2000: OFFSET_CAP.append(params); break   # Gamma refuses offsets past 2,000; tags and searches cover the rest
            try: d = get(G + "/events?" + urllib.parse.urlencode({"closed": "false", "limit": 100, "offset": off, **params}), tries=2)
            except RuntimeError: break
            if not d: break
            for e in d: seen.setdefault(e["id"], e)
            off += len(d); time.sleep(0.15)
    page_events({})
    for tag in ("politics", "elections", "us-politics", "us-elections", "ballot-measures", "midterms", "state-politics", "california", "florida", "washington"):
        page_events({"tag_slug": tag})
    queries = ["ballot measure", "proposition", "amendment", "initiative", "referendum", "ballot question", "measure pass", "Prop"] + [f"{st} ballot" for st in STATES]
    for q in queries:
        try: d = get(G + "/public-search?" + urllib.parse.urlencode({"q": q, "limit_per_type": 50, "events_status": "active", "search_tags": "false", "search_profiles": "false"}), tries=2)
        except RuntimeError: continue
        for e in d.get("events") or []:
            if e["id"] not in seen:
                try: seen[e["id"]] = get(G + f"/events/{e['id']}", tries=2)
                except RuntimeError: seen[e["id"]] = e
        time.sleep(0.15)
    events = list(seen.values())
    (RAW / "polymarket_open_events.json").write_text(json.dumps({"retrieved": NOW, "events": events}))
    rows = []
    for e in events:
        text = " ".join([e.get("title") or ""] + [m.get("question") or "" for m in e.get("markets") or []])
        us = any(st in text for st in STATES) or re.search(r"\b(NYC|New York City|Los Angeles|San Francisco|Chicago|Seattle|Denver|Portland|Boston|Honolulu|Miami|Austin|Houston|Dallas|Phoenix|Oakland|San Diego|San Jose|Sacramento|Philadelphia|Detroit|Atlanta|Minneapolis|Bay Area|county|city of)\b", text, re.I) or re.search(r"\b(Measure [A-Z]{1,2}|Prop(osition)? [A-Z0-9]{1,3})\b", text)
        why = ("no measure keyword" if not KW.search(text) else "no U.S. place named" if not us else "foreign" if FOREIGN.search(text) else "not a ballot measure" if NOT_MEASURE.search(e.get("title") or "") else "")
        CANDIDATES.append({"venue": "polymarket", "id": e.get("id"), "title": e.get("title"), "decision": "kept" if not why else "rejected", "reason": why})
        if why: continue
        for m in e.get("markets") or []:
            rows.append({"venue": "polymarket", "series": e.get("slug"), "series_title": e.get("title"), "event": e.get("id"), "market": m.get("id"),
                         "title": m.get("question"), "subtitle": m.get("groupItemTitle"), "status": "closed" if m.get("closed") else ("active" if m.get("active") else "inactive"),
                         "open_time": m.get("startDate") or m.get("createdAt"), "close_time": m.get("endDate"), "expected_expiration": m.get("endDate"),
                         "volume": m.get("volumeNum") or m.get("volume"), "volume_24h": m.get("volume24hr"), "open_interest": None,
                         "liquidity": m.get("liquidityNum") or m.get("liquidity"), "yes_bid": m.get("bestBid"), "yes_ask": m.get("bestAsk"),
                         "last": m.get("lastTradePrice"), "rules": (m.get("description") or "").replace("\n", " ")[:600],
                         "clob_token_ids": m.get("clobTokenIds")})
    return rows, len(events)

if __name__ == "__main__":
    kr, ns, nc = kalshi(); pr, ne = polymarket()
    for name, rows in (("kalshi", kr), ("polymarket", pr)):
        if not rows: continue
        with open(DER / f"markets_{name}.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) + (["clob_token_ids"] if "clob_token_ids" not in rows[0] else []), extrasaction="ignore")
            w.writeheader(); w.writerows(rows)
    with open(DER / "enumeration_candidates.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["venue", "id", "title", "decision", "reason"]); w.writeheader(); w.writerows(CANDIDATES)
    meta = {"retrieved": NOW, "complete": not REQUEST_LOG and KALSHI_SOURCE.startswith("live"), "request_failures": REQUEST_LOG, "gamma_offset_cap_reached": OFFSET_CAP, "kalshi_source": KALSHI_SOURCE, "kalshi_series_scanned": ns, "kalshi_candidate_series": nc, "kalshi_markets_kept": len(kr),
            "polymarket_open_events_scanned": ne, "polymarket_markets_kept": len(pr)}
    (DER / "enumeration_meta.json").write_text(json.dumps(meta, indent=1)); print(json.dumps(meta, indent=1))
