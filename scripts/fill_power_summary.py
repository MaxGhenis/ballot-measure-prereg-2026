"""Write the power paragraph of REGISTRATION.md section 7 from results/power.json, between the markers
<!-- power-summary:start --> and <!-- power-summary:end --> (or in place of [[POWER_SUMMARY]] the first time), so the
registration always states the numbers the power script produced. Run after scripts/power.py; scripts/freeze.sh runs it."""
import json, pathlib, re
ROOT = pathlib.Path(__file__).resolve().parents[1]
d = json.load(open(ROOT / "results/power.json")); A, B = d["A_election_night"], d["B_slow_count"]
f1 = lambda x: f"{x:.1f}"; f2 = lambda x: f"{abs(x):.2f}"; pc = lambda x: f"{round(100 * x)}%"
drawn = d["measures_drawn"]
text = (f"With 2,000 simulated outcomes of the {len(drawn)} measures drawn ({', '.join(drawn)}: every revenue measure with a freeze price in a "
        f"testable state, plus measures that enter only through a registered interaction), and every surprise realized on election night "
        f"(scenario A), the median smallest detectable β is {f1(A['mde_bp_per_bn']['median'])} basis points per $1 billion a year "
        f"(10th to 90th percentile, {f1(A['mde_bp_per_bn']['p10'])} to {f1(A['mde_bp_per_bn']['p90'])}). The benchmark's median is "
        f"−{f2(A['benchmark_bp_per_bn_median']['nmr_low_7bp'])} at its conservative end and −{f2(A['benchmark_bp_per_bn_median']['nmr_high_15bp'])} "
        f"at its upper end. The smallest detectable β falls below the benchmark's size in {pc(A['share_sims_mde_below_nmr_low'])} of simulated "
        f"outcomes at the conservative end and {pc(A['share_sims_mde_below_nmr_high'])} at the upper end. If only 60% of each surprise is realized "
        f"by November 6 (scenario B, a slow count), the median rises to {f1(B['mde_bp_per_bn']['median'])}, and those shares are "
        f"{pc(B['share_sims_mde_below_nmr_low'])} and {pc(B['share_sims_mde_below_nmr_high'])}. The panel has {d['n_placebo_days']} placebo days; "
        f"{len(d['measures_in_testable_states_without_freeze_price'])} revenue measures in testable states lack a freeze price.")
block = f"<!-- power-summary:start -->{text}<!-- power-summary:end -->"
p = ROOT / "REGISTRATION.md"; t = p.read_text()
if "[[POWER_SUMMARY]]" in t: t = t.replace("[[POWER_SUMMARY]]", block)
else: t = re.sub(r"<!-- power-summary:start -->.*?<!-- power-summary:end -->", lambda m: block, t, flags=re.S)
p.write_text(t); print(text)
