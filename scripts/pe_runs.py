"""PolicyEngine counterfactuals for November 3, 2026 measures that policyengine-us models (hosted API, static).
CA Proposition 3 keeps the Proposition 30/55 rates (10.3%, 11.3%, 12.3%) after 2030. policyengine-us 2.2.1 has no scheduled
expiry for them, so its current law is the Proposition 3 world; the reform lowers the three brackets to 9.3% from 2031, the
counterfactual in which Proposition 3 fails. Revenue maintained by Proposition 3 = minus the reform's state revenue impact.
Washington I-645 (repeal of the income tax on income over $1 million) reuses policy 98675 from the memo (tax off from 2028).
Requests and responses are saved under pe/api/."""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts"))
import pe_api
pe_api.OUT = pathlib.Path(__file__).resolve().parents[1] / "pe/api"; pe_api.OUT.mkdir(parents=True, exist_ok=True)
FS = ("single", "joint", "separate", "head_of_household", "surviving_spouse")
RUNS = {
    "ca_prop3_fails": ({f"gov.states.ca.tax.income.rates.{fs}[{i}].rate": {"2031-01-01.2100-12-31": 0.093} for fs in FS for i in (6, 7, 8)},
                       [("state/ca", 2031)]),
}
if __name__ == "__main__":
    for name, (data, regs) in RUNS.items():
        prev = pe_api.OUT / f"policy_{name}.json"
        pid = json.loads(prev.read_text())["response"]["result"]["policy_id"] if prev.exists() else pe_api.policy(name, data)
        print(name, "policy_id", pid, flush=True)
        for region, yr in regs:
            r = pe_api.economy(name, pid, region, yr)
            b = (r.get("result") or {}).get("budget") or {}
            print(f"  {region} {yr}: status={r.get('status')} state_tax_revenue_impact={b.get('state_tax_revenue_impact')} msg={str(r.get('message'))[:200]}", flush=True)
