"""Ex-ante power for the pooled test, from the frozen registry.

Inputs: registry/measures.csv (category R rows with F_annual_bn), registry/prices_at_freeze.csv (passage probability of each
measure's primary market at the freeze snapshot), registry/assets.csv (each testable state's instrument, benchmark and
durations), and the daily spread panel built by panel.py (placebo days).
For each simulation, every revenue measure passes with probability p (markets taken as calibrated). Its probability moves
by (outcome - p) in total over the window, a share `realized` of it by the window's end, spread evenly over the window's
days. X[s, t] = sum dp * F. The smallest detectable beta (bp per $ billion a year) is 2.8 x the placebo SE for that X, an approximation.
Also reports the benchmark from Novy-Marx and Rauh (2012): spreads rise 7 to 15 bp per 10% of state revenue lost, i.e.
beta_s = -(70 to 150) / R_s bp per $ billion for a state with R_s $ billion of tax revenue (Census FY2025), averaged
with weights sum_t X[s, t]^2. Writes results/power.json."""
import csv, json, pathlib, sys
import numpy as np
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from estimate import pooled_test
INTER = list(csv.DictReader(open(ROOT / "registry/interactions.csv"))) if (ROOT / "registry/interactions.csv").exists() else []

def load_inputs():
    allm = list(csv.DictReader(open(ROOT / "registry/measures.csv")))
    paired = {x for r in INTER if (r.get("F_joint_bn") or "").strip() for x in (r["measure_i"], r["measure_j"])}
    # revenue measures, plus any measure in a quantified interaction pair (it enters only through the pair, F = 0 alone)
    meas = [dict(r, F_annual_bn=(r["F_annual_bn"] if r["category"] == "R" else "0")) for r in allm
            if (r["category"] == "R" and r["F_annual_bn"] not in ("", None)) or r["measure_id"] in paired]
    p = {r["measure_id"]: float(r["p"]) for r in csv.DictReader(open(ROOT / "registry/prices_at_freeze.csv"))}
    panel = json.load(open(ROOT / "results/spread_panel.json"))
    states = list(panel["states"])           # every testable state; states with no revenue measure have X = 0
    Y = np.array([panel["spread_bp"][s] for s in states])          # (S, N) daily spread changes on placebo days, bp
    R = {s: v for s, v in panel["state_tax_revenue_bn"].items()}
    return meas, p, states, Y, R

def simulate(meas, p, states, Y, R, days=(1.0, 0.0, 0.0), sims=2000, seed=0):
    """days: share of each measure's total surprise realized on each event day (November 4, 5, 6)."""
    T = len(days); realized = float(sum(days))
    rng = np.random.default_rng(seed); idx = {s: k for k, s in enumerate(states)}
    mdes, betas_bench = [], []
    for _ in range(sims):
        X = np.zeros((len(states), T)); outc = {}
        for m in meas:
            if m["state"] not in idx or m["measure_id"] not in p: continue
            pi = p[m["measure_id"]]; out = float(rng.random() < pi); outc[m["measure_id"]] = (out, pi, float(m["F_annual_bn"]))
            X[idx[m["state"]], :] += np.array(days) * (out - pi) * float(m["F_annual_bn"])
        for r in INTER:   # registered pair interactions: the change in p_i p_j G_ij, G_ij = F_joint - F_i - F_j
            i, j = r["measure_i"], r["measure_j"]
            if not (r.get("F_joint_bn") or "").strip(): continue
            if i in outc and j in outc and r["state"] in idx:
                (oi, pi, Fi), (oj, pj, Fj) = outc[i], outc[j]
                X[idx[r["state"]], :] += np.array(days) * (oi * oj - pi * pj) * (float(r["F_joint_bn"]) - Fi - Fj)
        if not np.any(X): continue
        r = pooled_test(np.zeros_like(X), X, Y)        # the SE does not depend on y
        if r["status"] != "OK": continue
        mdes.append(r["mde"])
        w = (X ** 2).sum(axis=1)
        if w.sum() > 0:
            betas_bench.append([float((w * np.array([-70.0 / R[s] for s in states])).sum() / w.sum()),
                                float((w * np.array([-150.0 / R[s] for s in states])).sum() / w.sum())])
    mdes = np.array(mdes); bb = np.array(betas_bench)
    q = lambda a, x: float(np.quantile(a, x))
    return {"sims": int(len(mdes)), "days": list(days), "realized_by_nov6": realized,
            "mde_bp_per_bn": {"p10": q(mdes, 0.1), "median": q(mdes, 0.5), "p90": q(mdes, 0.9)},
            "benchmark_bp_per_bn_median": {"nmr_low_7bp": q(bb[:, 0], 0.5), "nmr_high_15bp": q(bb[:, 1], 0.5)},
            "share_sims_mde_below_nmr_low": float(np.mean(mdes < np.abs(bb[:, 0]))),
            "share_sims_mde_below_nmr_high": float(np.mean(mdes < np.abs(bb[:, 1])))}

if __name__ == "__main__":
    meas, p, states, Y, R = load_inputs()
    import hashlib
    INPUTS = ["registry/measures.csv", "registry/prices_at_freeze.csv", "registry/interactions.csv", "registry/assets.csv", "results/spread_panel.json"]
    out = {"inputs_sha256": {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in INPUTS},
           "states": states, "n_placebo_days": int(Y.shape[1]),
           "measures_drawn": [m["measure_id"] for m in meas if m["state"] in states and m["measure_id"] in p],
           "measures_in_testable_states_without_freeze_price": [m["measure_id"] for m in meas if m["state"] in states and m["measure_id"] not in p],
           "measures_in_untestable_states": [m["measure_id"] for m in meas if m["state"] not in states]}
    # A: every surprise realized on November 4 (calls on election night). B: slow count, 60% realized by November 6.
    for name, days in (("A_election_night", (1.0, 0.0, 0.0)), ("B_slow_count", (0.4, 0.1, 0.1))):
        out[name] = simulate(meas, p, states, Y, R, days=days)
    (ROOT / "results").mkdir(exist_ok=True)
    json.dump(out, open(ROOT / "results/power.json", "w"), indent=1)
    print(json.dumps(out, indent=1))
