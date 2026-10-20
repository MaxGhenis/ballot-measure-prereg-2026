"""registry/markets.csv: one row per registered market, with what capture.py needs (series, open and close times, CLOB
token ids for Polymarket) and the measure it belongs to. Built from the enumeration and registry/measures.csv."""
import csv, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
src = {}
for venue in ("kalshi", "polymarket"):
    for r in csv.DictReader(open(ROOT / f"data/derived/markets_{venue}.csv")): src[f"{venue}:{r['market']}"] = r
rows = []
for m in csv.DictReader(open(ROOT / "registry/measures.csv")):
    for k in [k for k in m["markets"].split(";") if k and not k.startswith("pending-series:")]:
        if k not in src: print("missing", k); continue
        r = src[k]; venue = k.split(":")[0]
        rows.append({"measure_id": m["measure_id"], "venue": venue, "series": r["series"], "market": r["market"], "open_time": r["open_time"],
                     "close_time": r["close_time"], "clob_token_ids": r.get("clob_token_ids", ""), "volume_at_enumeration": r["volume"]})
with open(ROOT / "registry/markets.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print(len(rows), "markets")
