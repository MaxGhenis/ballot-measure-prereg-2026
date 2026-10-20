"""Build the daily spread panel and freeze-time probabilities from captured raw data.

Spread change for state s on trading day t, in basis points of yield (duration-matched):
    y[s, t] = -( r_state[t] / D_state - r_bench[t] / D_bench ) * 100,  r = 100 * daily log return of adjusted closes (%),
where the state leg averages its instruments' returns and the benchmark leg averages its own (registry/assets.csv; only
rank-1 instruments enter the primary test). Placebo days: the 250 trading days ending October 30, 2026, minus November 5-7,
2025 (after the November 4, 2025 election) and any day a leg has no price. Writes results/spread_panel.json.
Usage: python scripts/panel.py [capture_dir]"""
import csv, datetime as dt, json, pathlib, sys
import numpy as np, pandas as pd
ROOT = pathlib.Path(__file__).resolve().parents[1]
PLACEBO_END, N_PLACEBO = "2026-10-30", 250
EXCLUDE = ["2025-11-05", "2025-11-06", "2025-11-07"]

def yahoo_daily(cap, t):
    d = json.load(open(cap / f"yahoo_{t}_1d.json"))["data"]["chart"]["result"][0]
    ts = pd.to_datetime(d["timestamp"], unit="s", utc=True).tz_convert("America/New_York").normalize().tz_localize(None)
    adj = (d["indicators"].get("adjclose") or [{}])[0].get("adjclose") or d["indicators"]["quote"][0]["close"]
    return pd.Series(adj, index=ts, dtype=float).dropna()

def leg(cap, tickers):
    r = pd.concat([100 * np.log(yahoo_daily(cap, t)).diff() for t in tickers], axis=1)
    return r.mean(axis=1, skipna=False)

def spreads(cap, assets):
    out = {}
    for a in assets:
        if a["rank"] != "1": continue
        ys = leg(cap, a["tickers"].split(";")); yb = leg(cap, a["benchmark"].split(";"))
        y = -(ys / float(a["duration_state"]) - yb / float(a["duration_bench"])) * 100
        out[a["state"]] = y.dropna()
    df = pd.DataFrame(out).dropna()
    df = df[~df.index.isin(pd.to_datetime(EXCLUDE))]
    return df.loc[:PLACEBO_END].iloc[-N_PLACEBO:]

if __name__ == "__main__":
    cap = (pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else sorted((ROOT / "data/raw/capture").iterdir())[-1])
    assets = list(csv.DictReader(open(ROOT / "registry/assets.csv")))
    df = spreads(cap, assets)
    tax = json.load(open(ROOT / "evidence/census/stc_2025_total_taxes.json"))["states"]
    names = {r["abbr"]: r["name"] for r in csv.DictReader(open(ROOT / "registry/state_codes.csv"))}
    R = {s: tax[names.get(s, s)]["total_taxes_thousands"] / 1e6 for s in df.columns if names.get(s, s) in tax}
    panel = {"capture": str(cap.relative_to(ROOT)), "placebo_end": PLACEBO_END, "n_days": int(len(df)), "first_day": str(df.index[0].date()),
             "last_day": str(df.index[-1].date()), "states": list(df.columns), "spread_bp": {s: [float(v) for v in df[s]] for s in df.columns},
             "sd_bp": {s: float(df[s].std()) for s in df.columns}, "state_tax_revenue_bn": R}
    (ROOT / "results").mkdir(exist_ok=True)
    json.dump(panel, open(ROOT / "results/spread_panel.json", "w"), indent=1)
    print({k: v for k, v in panel.items() if k != "spread_bp"})
