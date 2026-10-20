"""Apply the fiscal-category audit (lanes/out-audit_{CA,WEST,EAST}.md) to registry/measures.csv and write
registry/interactions.csv. Run once from prereg-nov2026/: python3 lanes/apply_audit.py

- Every audited row takes the audit's category, F, sign, timing, horizon, coverage, one-time and debt-service fields,
  official quote, source and notes (column audit_notes).
- San Francisco's combined A-G row is replaced by one row per proposition, each mapped to its Kalshi market.
- Honolulu Charter Question 4 is added.
- One-time years: a number only where the official estimate names a span; otherwise blank (REGISTRATION.md: three years).
- Nebraska Initiative 441's sign is set to 0 for the RU sensitivity: the audit treats 440 and 441 as one regime whose
  payoffs must not be added.
- interactions.csv: Colorado NN x 137 (joint total 0.521, the audit's overlap rule from official figures) and Amendment 87
  x Proposition 136 (joint total unquantified; bounds 0 and 1.972 from the two legal outcomes; registered midpoint 0.986),
  plus every other documented pair with an empty joint figure (flagged, additive)."""
import csv, io, pathlib, re
ROOT = pathlib.Path(__file__).resolve().parents[1]
reg = list(csv.DictReader(open(ROOT / "registry/measures.csv")))
audit = {}
for g in ("CA", "WEST", "EAST"):
    t = (ROOT / f"lanes/out-audit_{g}.md").read_text()
    for block in re.findall(r"```csv\n(.*?)```", t, re.S):
        rows = list(csv.DictReader(io.StringIO(block)))
        if rows and "new_category" in rows[0]:
            for r in rows: audit[r["measure_id"]] = dict(r, lane=g)

NEW_COLS = ["F_sign", "F_horizon", "F_coverage", "onetime_bn", "onetime_years", "audit_notes", "audit_lane"]
fields = list(reg[0].keys()) + [c for c in NEW_COLS if c not in reg[0]]
num = lambda x: (x.strip() if re.fullmatch(r"-?\d+(\.\d+)?", (x or "").strip()) else "")


def merged(base, a):
    r = dict(base)
    r.update(category=a["new_category"], F_annual_bn=a["F_annual_bn"], F_sign=a["F_sign"], F_first_year=a["F_first_year"],
             F_horizon=a["F_horizon"], F_coverage=a["F_coverage"], onetime_bn=a["onetime_bn"], onetime_years=num(a["onetime_years"]),
             debt_service_bn_per_year=a["debt_service_bn_per_year"], fiscal_quote=a["fiscal_quote"], fiscal_source=a["fiscal_source"],
             audit_notes=(a["notes"] + (f" One-time timing (official text): {a['onetime_years']}" if a["onetime_years"] and not num(a["onetime_years"]) else "")),
             audit_lane=a["lane"])
    if r["category"] not in ("R",): r["F_basis"] = r["F_basis"] if r["category"] == "R" else ""
    return r


out = []
for b in reg:
    mid = b["measure_id"]
    if mid == "CA-SF-PropsABCDEFG":
        for L in "ABCDEFG":
            a = audit[f"{mid}-{L}"]
            title = re.search(r"Title: ([^.]+)\.", a["notes"]).group(1)
            r = merged({k: "" for k in fields} | {"state": "CA-local", "official_number": f"San Francisco Proposition {L}", "official_title": title,
                                                  "markets": f"kalshi:KXSFBALLOTMEASURES-26NOV03-PR{L}"}, a)
            r["measure_id"] = f"{mid}-{L}"; r["state"] = b["state"]; out.append(r)
        continue
    out.append(merged(b, audit[mid]) if mid in audit else b)
hq = audit["HI-local-Honolulu-Q4"]
out.append(merged({k: "" for k in fields} | {"measure_id": "HI-local-Honolulu-Q4", "state": "HI", "official_number": "Honolulu Charter Question 4",
                                             "official_title": "Equity & Inclusion (P239)", "markets": "kalshi:KXHONOLULUQ4-26NOV03"}, hq))
for r in out:
    if r["measure_id"] == "NE-Initiative441":
        r["F_sign"] = "0"; r["audit_notes"] += " Sign set to 0 for the RU sensitivity: one regime with Initiative 440, payoffs not added."
with open(ROOT / "registry/measures.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows([{k: r.get(k, "") for k in fields} for r in out])

FS = "https://content.leg.colorado.gov/sites/default/files/2026-fiscal-impact-statements-english-accessible.pdf"
SFP = "https://media.api.sf.gov/documents/N26_EN_VIP.pdf"
I = [
    ("CO", "CO-PropositionNN", "CO-Proposition137", "0.521", "", "", "overlap rule from official figures (lanes/out-audit_WEST.md): both pass retain 0.521, the NN total", "https://leg.colorado.gov/ballots/direct-sporting-goods-sales-tax-revenue-for-conservation-2/files/blue-book p.5",
     "will reduce the amount of money the state actually keeps and spends under Proposition NN"),
    ("CO", "CO-Amendment87", "CO-Proposition136", "0.986", "0", "1.972", "joint receipts unquantified; bounded by the two legal outcomes (136 prevails: 0; 87 prevails: 1.972); registered midpoint", FS + " PDF p.20",
     "depending upon the resolution of this conflict"),
    ("CO", "CO-Proposition132", "CO-PropositionNN", "", "", "", "inferred shared TABOR refund pool; no joint figure", FS + " PDF p.40", "required to be refunded to taxpayers"),
    ("CA", "CA-P40", "CA-P41", "", "", "", "relative-vote contingency; no joint figure", "https://vig.cdn.sos.ca.gov/2026/general/pdf/prop41.pdf p.59",
     "then Proposition 40 could be stopped from becoming law even if it gets yes votes from a majority of voters"),
    ("CA", "CA-P40", "CA-P42", "", "", "", "relative-vote contingency; no joint figure", "https://vig.cdn.sos.ca.gov/2026/general/pdf/prop42.pdf p.63",
     "This is because the courts could find that Proposition 42 conflicts with Proposition 40."),
    ("CA", "CA-SF-PropI", "CA-SF-PropJ", "", "", "", "both amend transfer-tax law; overlapping receipts; no joint figure", SFP + " pp.234,239-240", "this Measure shall prevail over the other measure to the extent they are in conflict"),
    ("CA", "CA-SF-PropsABCDEFG-A", "CA-SF-PropsABCDEFG-E", "", "", "", "conditional joint provision; costs unquantified", SFP + " p.181", "If this measure is enacted and the measure titled"),
    ("CA", "CA-SF-PropsABCDEFG-A", "CA-SF-PropsABCDEFG-F", "", "", "", "management overlap; no fiscal figure", SFP + " p.181", "In case of an actual conflict in Section 15.105"),
    ("NE", "NE-Initiative440", "NE-Initiative441", "", "", "", "one wagering regime; payoffs not additive; no official figure", "https://sos.nebraska.gov/sites/default/files/doc/elections/2026/2026%20Ballot%20Measures%20Pamphlet.pdf printed pp.4, 7-8", "to the full extent permitted by the Constitution of Nebraska"),
    ("LA", "LA-Amendment6Act274", "LA-Amendment9Act220", "", "", "", "eligibility interaction; no joint figure", "https://www.legis.la.gov/legis/ViewDocument.aspx?d=1476071 p.2", "qualifies for the special assessment level"),
    ("LA", "LA-Amendment6Act274", "LA-Amendment10Act272", "", "", "", "drafting overlap (both add Art. VII, Sec. 21(P)); no joint figure", "https://www.legis.la.gov/legis/ViewDocument.aspx?d=1475810 p.1", "add Article VII, Section 21(P)"),
    ("MA", "MA-Question5", "MA-Question8", "", "", "", "inferred revenue-base interaction; no joint figure", "https://www.sec.state.ma.us/divisions/elections/research-and-statistics/2026-Information-for-voters/2026-ballot-question5.htm", "immediately preceding fiscal year"),
    ("FL", "FL-Amendment2", "FL-Amendment3", "", "", "", "no documented contingency; different benchmark years; listed so per-measure estimates are flagged", "https://edr.state.fl.us/Content/conferences/revenueimpact/archives/2026F/_pdf/impact0710.pdf pp.683-685", "all non-agricultural parcels"),
]
with open(ROOT / "registry/interactions.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["state", "measure_i", "measure_j", "F_joint_bn", "F_joint_low_bn", "F_joint_high_bn", "basis", "source", "quote"]); w.writerows(I)
ids = {r["measure_id"] for r in out}
assert all(i in ids and j in ids for _, i, j, *_ in I), [x for x in I if x[1] not in ids or x[2] not in ids]
print(len(out), "measures;", len(I), "interaction records")
