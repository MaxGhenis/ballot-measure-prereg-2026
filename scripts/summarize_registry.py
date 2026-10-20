"""registry/SUMMARY.md: measures by state and category, and every revenue measure with its official estimate and freeze price."""
import collections, csv, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
M = list(csv.DictReader(open(ROOT / "registry/measures.csv")))
P = {r["measure_id"]: r for r in csv.DictReader(open(ROOT / "registry/prices_at_freeze.csv"))}
K = list(csv.DictReader(open(ROOT / "registry/markets.csv")))
A = {r["state"]: r for r in csv.DictReader(open(ROOT / "registry/assets.csv")) if r["rank"] == "1"}
cats = ["R", "RU", "B", "O", "N"]
by = collections.defaultdict(collections.Counter)
for m in M: by[m["state"]][m["category"]] += 1
L = ["# Registry summary", "",
     f"{len(M)} measures in {len(by)} states or localities, {len(K)} markets ({sum(r['venue'] == 'kalshi' for r in K)} Kalshi, {sum(r['venue'] == 'polymarket' for r in K)} Polymarket).",
     "Categories: R, revenue measure with an official annual estimate; RU, revenue measure without one; B, bond authorization; O, other fiscal; N, no material fiscal effect (the placebo set).", "",
     "| State | " + " | ".join(cats) + " | Testable spread |", "|---|" + "---:|" * len(cats) + "---|"]
for s in sorted(by):
    a = A.get(s); L.append(f"| {s} | " + " | ".join(str(by[s][c]) for c in cats) + f" | {a['tickers'] + ' vs ' + a['benchmark'] if a else 'none'} |")
L += ["", "## Revenue measures (category R)", "", "| Measure | State | F, $ billion a year | Basis | Primary market | Freeze p |", "|---|---|---:|---|---|---:|"]
for m in M:
    if m["category"] != "R": continue
    p = P.get(m["measure_id"], {})
    L.append(f"| {m['measure_id']} | {m['state']} | {float(m['F_annual_bn']):+.3f} | {m['F_basis']} | {p.get('primary_market', '')} | {float(p['p']):.3f} |" if p else f"| {m['measure_id']} | {m['state']} | {m['F_annual_bn']} | {m['F_basis']} | none | |")
(ROOT / "registry/SUMMARY.md").write_text("\n".join(L) + "\n")
print("\n".join(L[:6]))
