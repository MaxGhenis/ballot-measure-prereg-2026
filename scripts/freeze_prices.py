"""Freeze-time passage probability for each registered measure (registry/prices_at_freeze.csv).
Primary market: of the markets listed for the measure, the one with the most volume at the snapshot (Kalshi contracts and
Polymarket dollars are compared as numbers, as the venues report them). Probability: bid-ask midpoint when there is an ask
above 0 and the spread is 10 cents or less, otherwise the last trade (the memo's rule; the same quote rule as
run_analysis.kalshi_points). A bid and ask both at 0 is no quote. A market that has never traded and has no such quote has no
price; its measure is listed in registry/unpriced_at_freeze.csv and stays out of every test. Sources: data/derived/markets_kalshi.csv and
markets_polymarket.csv from scripts/enumerate_markets.py, with their retrieval times."""
import csv, json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
f = lambda x: float(x) if x not in ("", None) else None
mk = {}
for venue in ("kalshi", "polymarket"):
    for r in csv.DictReader(open(ROOT / f"data/derived/markets_{venue}.csv")):
        mk[f"{venue}:{r['market']}"] = r
meta = json.load(open(ROOT / "data/derived/enumeration_meta.json"))
rows, unpriced = [], []
for m in csv.DictReader(open(ROOT / "registry/measures.csv")):
    cands = [(k, mk[k]) for k in m["markets"].split(";") if k in mk]
    if not cands: continue
    k, r = max(cands, key=lambda kr: f(kr[1]["volume"]) or 0)
    b, a, last = f(r["yes_bid"]), f(r["yes_ask"]), f(r["last"])
    if not (f(r["volume"]) or 0): last = None          # a never-traded market reports last price 0; that is not a price
    p, rule = ((a + b) / 2, "midpoint") if b is not None and a is not None and a > 0 and a - b <= 0.10 else (last, "last trade")
    if p is None:
        unpriced.append({"measure_id": m["measure_id"], "primary_market": k, "reason": "never traded and no quote with an ask above 0 within 10 cents"}); continue
    snap = meta["kalshi_source"] if k.startswith("kalshi") else f"live {meta['retrieved']}"
    rows.append({"measure_id": m["measure_id"], "primary_market": k, "volume": r["volume"], "p": p, "rule": rule, "snapshot": snap})
with open(ROOT / "registry/prices_at_freeze.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
with open(ROOT / "registry/unpriced_at_freeze.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["measure_id", "primary_market", "reason"]); w.writeheader(); w.writerows(unpriced)
print(len(rows), "priced;", len(unpriced), "unpriced")
