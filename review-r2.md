# Round-2 review: November 3, 2026 ballot-measure pre-registration (commit `a64cc99`)

## Verdict: MAJOR FIXES (two findings, both small)

Most of round 1 is properly fixed: the gate, unestimable handling, capture, W2/W3, the three asset states and the San Francisco split. Two major findings remain:

- **A87 × 136 lower bound.** The rule pairing Amendment 87 with Proposition 136 sets a lower bound that the official analysis contradicts. Because the bound is wrong, the bounds sensitivity doesn't bracket the possible outcomes.
- **Which capture feeds the registered reading.** The registration doesn't say which capture W1 uses, and the runbook's timing can make the primary test UNESTIMABLE.

Both fixes are a few hours' work. Everything else below is minor or a nit.

## Round-diff

| # | Round-1 finding | Status | What I checked in the files |
|---|---|---|---|
| 1 | W2, W3 and secondary specifications missing | **Fixed, with gaps** | All windows and specifications exist in `run_analysis.py`. The PolicyEngine specification is wrong, and two specifications drop interactions (m6, m7). The W2 test only exercises the case where every market has already settled (m8). |
| 2 | Benchmark called a lower bound | **Fixed** | §6 now says illustrative and conditional, names the population and the mapping caveats, and limits what REFUTE means. "Lower bound" is gone. |
| 3 | Category-N gate ignored | **Fixed, one hole** | H3 is computed before `classify()`, and a failed gate turns CONFIRM into INCONCLUSIVE. But any H3 failure, not just "no N measure moved", counts as untestable and lets CONFIRM through (m1). |
| 4 | Control definition and N set | **Fixed** | `joint_test` is a valid conditional test. The four named rows are recoded (NM A4 → O, CO A84 → RU, AZ 144 → O, CA P5 → O). New issues: CO-132 (m4) and design notes (m11). |
| 5 | Capture sequence | **Fixed** | `capture.py all` writes one stamped directory with a manifest, and tickers come from `assets.csv`. |
| 6 | Missing data | **Fixed** | `_validate` blocks NaN, zero exposure and too few blocks, and the NaN case now returns UNESTIMABLE. Fallback and omission rules are implemented, but the fallback test never exercises a fallback (m8). |
| 7 | Settlement values | **Partly fixed** | Market records are captured and applied. But the settlement time comes from Kalshi's `close_time`, registered as 2027-11-02, which was never tested against a real early-closed market. Polymarket falls back to `endDate`, which can wipe out W1's movement (m2). |
| 8 | Power wording | **Fixed** | `measures_drawn` is recorded, the §7 paragraph is generated from `power.json`, and the MDE is "about 2.8 × SE". |
| 9 | Federal-election history | **Fixed** | `evidence/history/` holds 23 files plus a manifest. "Previous trading day" isn't strictly enforced (nit). |
| 10 | Colorado additivity | **Partly fixed; newly wrong** | NN × 137 is correct. **The A87 × 136 bounds are wrong (M1).** |
| 11 | Inventory | **Fixed** | Foreign-place filters are anchored, "term limits" is no longer excluded, candidates are saved, the offset cap is recorded, A–G is split, and no `pending-series:` entries remain. |
| 12 | AR, WI, WV wrongly excluded | **Fixed** | `assets.csv` lists MFARX 7.56, WWTFX 6.68 and MFWVX 7.51: 21 testable states. |
| 13 | Timing and horizons | **Fixed for R rows** | CA-P40 "not stated", SF-J "5 years", WY "state; local not estimated". Many non-R rows still have a blank `F_first_year`, so "every row" overstates (nit). |
| 14 | No independent timestamp | **Fixed, with caveats** | OpenTimestamps is added and FREEZE.md lists the exclusions. The script isn't safe to rerun if stamping fails, and a private timestamp doesn't prove there was only one registration (m9, m10). |

## New findings

**M1 [major]. The A87 × 136 lower bound is wrong.**
- **Text:** `registry/interactions.csv` row 3 and REGISTRATION §3.2: "bounded by the two legal outcomes (136 prevails: 0; 87 prevails: 1.972); registered midpoint 0.986".
- **Official source (fiscal impact statements, PDF p.20):** "If both … are approved … the proposed tax rates for income over $500,000 in Amendment 87 would be higher than the 4.4 percent limit … revenue impacts may be different … depending upon the resolution of this conflict."
- **Why 0 is not a bound:** only the brackets above $500,000 conflict with the cap. A87's 3.7% and 4.2% brackets (PDF p.19, Table 2) sit under 136's cap and would survive if 136 prevails on the top rates. That outcome is a revenue loss, not zero.
- **Rough size of that loss (my calculation from PDF p.20, needs checking):**
  - 3.4 million filers × −$176 ≈ −$0.60 billion;
  - 64,000 high earners × about −$325 on their first $100,000 ≈ −$0.02 billion;
  - so the lower bound is about −$0.62 billion, and the range is roughly [−0.62, 1.972] with a midpoint near 0.68.
- **The research lane didn't supply these bounds.** `out-audit_WEST.md:106` advised excluding the pair from the confirmatory exposure "unless a separate treatment … is frozen". The 0 and 1.972 bounds were added later in `apply_audit.py`.
- **Fix:** do one of the following, then regenerate power and update §3.2 and the CSV notes.
  - Register three outcomes (87 prevails, 1.972; 136 voids A87, 0; 136 caps the top rates, about −0.62), with the midpoint of the full range as primary and the extremes as the bounds.
  - Or follow the lane: leave the both-pass state out of the primary exposure, and report it only as bounded secondaries.

**M2 [major]. The registered reading depends on which capture is used, and the scheduled capture can miss NAVs.**
- **NAV timing:** in capture `20261016T224731Z`, the `regularMarketTime` values show the October 16 NAVs arriving at:
  - 6:13 p.m. ET for Franklin funds;
  - 6:26–6:28 p.m. for Nuveen, MFS and Allspring.
- **Runbook timing:** RUNBOOK step 2 says to capture "after 6 p.m." on November 6.
- **What a missing NAV does:** if any tier-2 fund lacks its November 6 bar, `y` contains NaN and the whole primary test is UNESTIMABLE. That's because `_validate` rejects the window, and no registered rule drops just that state.
- **No registered capture:** the runbook says "latest stamp", and nothing in REGISTRATION ties a window to a capture. W1 results really do change from one capture to another: settlement overrides, revised adjusted closes and fallback availability all differ. Rerunning on later captures is an unregistered fork.
- **Fix:**
  - Register that W1 and W0 use the first capture after November 6 in which every rank-1 instrument has bars for November 3–6; W3 uses the November 4 capture; W2 uses December 14.
  - Register what happens to a state still missing a bar on November 9: dropped and listed, or the test is unestimable.
  - Add a preflight in `run_analysis.py` that lists missing event-day bars per state before any estimate.
  - Move the runbook capture to after 9 p.m. ET.
  - Treat any rerun on another capture as a deviation in `DEVIATIONS.md`.

**m1 [minor]. The gate is waived on any H3 failure.**
- **Code:** `estimate.py:134` treats `h3` with any status other than OK as untestable, so collinearity or another failure still allows CONFIRM. §6 allows "untestable" only "because no category N measure moved".
- **Fix:** mark the gate untestable only when `XN` is all zero. Any other H3 UNESTIMABLE should give a status that blocks CONFIRM. Add a test.

**m2 [minor]. Settlement timing hasn't been checked against real records.**
- **Kalshi:**
  - `kalshi_settlement` prefers `close_time` over `settlement_ts`.
  - Every registered Kalshi market has `close_time` 2027-11-02 with `can_close_early: true`.
  - If Kalshi doesn't rewrite `close_time` when it closes a market early, the settlement value is never applied, and the last candle price carries forward with no warning.
  - The status list also omits "amended".
- **Polymarket:** the `endDate` and `umaEndDate` fallbacks can come before the actual resolution. If either precedes the November 3, 4 p.m. baseline, the baseline itself takes the settled value and that measure's movement disappears.
- **Fix:**
  - Kalshi: use `settlement_ts`, otherwise `close_time` only if it is at or before the capture time. Validate both on a settled 2025 `can_close_early` market record and save it as a test fixture.
  - Polymarket: require `closedTime`.

**m3 [minor, judgment call]. MA-Q8 sits in RU although the official statement gives a number.**
- **What the official statement says:** repeal "would reduce the amount" of receipts, and taxation of retail sales "raised approximately $280 million in state revenue and $50 million in local revenue" in FY2025.
- **The rule:** R is defined as "gives a number for the change".
- **What the audit did:** it added a test that isn't in the registration ("no attributable full-effect loss forecast").
- **Why it matters:** Massachusetts is testable.
- **Fix:** register MA-Q8 as R at −0.330 from FY2028-29, or add that exclusion to §3.2 explicitly and run R = −0.330 as a secondary specification.

**m4 [minor]. CO-132 is R, but its receipts are refunded.**
- **Official figures (PDF p.40):** "State Revenue $73,231" and "Change in TABOR Refunds $73,231". Net retention is zero, whereas NN and 137 are scored on retained receipts.
- **Side effects of the current coding:**
  - Its $8.9 million to $24.8 million in costs drop out of the O specification.
  - Its per-measure `b/F` explodes.
  - It shifts the median used for the RU specification.
- **Fix:** score F = 0 as retained receipts (category N or O by its costs), or code it O.

**m5 [minor]. The RU sensitivity has no materiality floor.**
- **Trivial measures get the full median:** CO-A84's possible fees are bounded by its costs of at most $1.24 million, yet it gets +$0.34 billion (the median |F|).
- **Double count:** CO-136 gets −$0.34 billion on its own, although the official finding is "no fiscal impact", and its effect is already in the pair term.
- **Fix:** apply the $10 million threshold to RU, cap RU values at any official bound, and set 136's sign to 0 for this specification.

**m6 [minor]. The PolicyEngine specification keeps only measures with a PolicyEngine number.**
- **Code:** `run_analysis.py:288` builds X from `pe_F_annual_bn` only, so every measure except CA-P3 drops out (WA is untestable).
- **Fix:** use the PolicyEngine figure where it exists and the official figure otherwise, with interactions.

**m7 [minor]. Interactions are inconsistent across specifications.**
- The revenue-share and PolicyEngine specifications drop interactions.
- The per-measure `joint_with` flag ignores `interactions.csv`, which §5.2 requires.

**m8 [minor]. Several tests don't test what they claim.**
- `test_null_near_zero`'s classification check is tautological, because CONFIRM always implies p < .05.
- `test_recovers_planted_effect` accepts INCONCLUSIVE.
- `test_fallback_and_omission` never runs a fallback. The synthetic capture writes files only for primary markets, and the either-or assertion passes when the measure is simply omitted.
- W2 is tested only for the all-settled case, and W3 only for the UNESTIMABLE case.
- Nothing tests H3 wired into `run()`, Polymarket settlement, or a pair whose second member isn't R (the A87 × 136 pattern).
- `tests/last_run.txt` still says "8 passed".

**m9 [minor]. `freeze.sh` can't be rerun after a failure.**
- **Failure mode:** `ots stamp` runs after the commit and the tag. If the calendars are blocked, `set -e` stops the script, and a rerun fails at `git commit` because nothing changed (and the tag already exists).
- **Stale power:** it doesn't rerun `panel.py` or `power.py`, so `power.json` can be out of date.
- **Unstable checksums:** `.hypothesis/` is included in the checksums and changes on later test runs.
- **Fix:** stamp before committing or make the steps idempotent, check that `power.json` matches the registry, and exclude `.hypothesis/`.

**m10 [minor]. A private timestamp proves existence, not uniqueness.**
- Several variant registrations could each be stamped, and any one revealed later.
- **Fix:** an embargoed OSF registration, or publishing the `SHA256SUMS` hash, closes this. That decision is Max's.
- Also, `run_analysis.py` doesn't check the registry or scripts against `SHA256SUMS` at run time. A check whose result is recorded in each output would make tampering visible.

**m11 [minor, design]. The H3 placebo set is a weak control.**
- `X_N` with F = 1 tests only a common-direction "passage" effect.
- The N set includes tax limits that credit analysts treat as relevant to revenue, such as NC's 3.5% income tax cap and AZ-141's ban on vehicle-mile taxes. Both are correctly N under the rule; NC's official note says no fiscal impact.
- **Fix:** report, without gating on it, an H3 that leaves out tax-limit N measures.

**Nits**
- If `manifest.json` is missing, the string "no manifest" is reported as 11 failures.
- `panel.py`'s docstring says it writes `prices_at_freeze.csv`; it doesn't.
- `federal_check` takes differences across gaps in the archive instead of requiring the previous trading day.
- W3 samples probabilities at 15:55 but takes the price from the bar that closes at 16:00.

## Registry audit (20 checks against official sources)

| Row | Result |
|---|---|
| CO-A87 | ✓ $1,972.0 million FY2027-28; exempt from TABOR (PDF pp.17–20) |
| CO-NN | ✓ refunds of $521.0 million eliminated (pp.23–28) |
| CO-137 | ✓ refunds reduced by $175.0 million (p.54 summary, p.64 TABOR section) |
| CO-136 | ✓ "no fiscal impact" on its own (pp.52–53); RU is defensible |
| CO-132 | Figure matches, but the receipts are refunded (m4) |
| CO-A84 | ✓ "fees may need to be raised"; costs $1,241,228, $260,000 and $555,500 match |
| NN × 137 joint 0.521 | ✓ follows from p.28 (refunds of $521.0 million under current law, which NN eliminates) |
| A87 × 136 | ✗ (M1) |
| CA-P3 | ✓ $5–15 billion (saved LAO text) |
| CA-P40 | ✓ "less than $1 billion per year"; "tens of billions … spread across several years" |
| CA-P44 | ✓ RU: low tens of millions in costs, covered by fees |
| WY-I1 | ✓ ($92,614,266) FY2028, state only |
| FL-A2 | ✓ (31.0) in 2027-28, Revenue Estimating Conference 2025, p.564 |
| MA-Q8 | Quote ✓; category questionable (m3) |
| MA-Q5 | ✓ no dollar figure found |
| NC 3.5% cap (N) | ✓ "No Fiscal Impact"; projected rates are below the cap |
| VA-Q1 (N on text) | ✓ the only fiscal statement is a $205,000 FY2027 publication cost |
| AR Issue 1 (N on text) | ✓ keeps the existing photo-ID provisions and adds the citizen-only clause |
| SF H, J, I and RTM | ✓ $177 million, $100–150 million, about $1 million and $980 million all appear in the saved pamphlet text |
| SF A–G split | ✓ PRA–PRG match Kalshi's "Will Proposition X pass?" titles in `markets_kalshi.csv`. D, E and F are N on "minimal impact" quotes. All seven are unpriced at the freeze. |

`apply_audit.py` carried these rows across faithfully. The NE-441 sign is set to 0, Honolulu Q4 is added, and the interactions match the script's list.

## How I verified
- Read every script, test, registry file and the runbook named in the prompt, plus the lane outputs for Colorado.
- Read the Colorado fiscal statement PDF pages directly. Checked the NC, Virginia, Arkansas, Wyoming and Florida PDFs, and the saved LAO and San Francisco texts. Used a web search for the MA-Q8 and MA-Q5 statements.
- Checked Yahoo's `regularMarketTime` in the October 16 capture.
- I couldn't run code here, so the tests and the power figures were not re-executed.
- No files were changed and nobody was contacted.

Sources:
- [Colorado 2026 fiscal impact statements](https://content.leg.colorado.gov/sites/default/files/2026-fiscal-impact-statements-english-accessible.pdf)
- [MA Question 8](https://www.sec.state.ma.us/divisions/elections/research-and-statistics/2026-Information-for-voters/2026-ballot-question8.htm)
- [MA Question 5](https://www.sec.state.ma.us/divisions/elections/research-and-statistics/2026-Information-for-voters/2026-ballot-question5.htm)
- [NC fiscal note SB 1080](https://www.ncleg.gov/Sessions/2025/FiscalNotes/Senate/PDF/SFN1080v1.pdf)
- [LAO Proposition 40](https://lao.ca.gov/ballot/2026/prop40-110326.pdf)
- [Wyoming ballot propositions](https://sos.wyo.gov/Elections/Docs/2026/2026_Statewide_Ballot_Propositions.pdf)
- [Florida Revenue Estimating Conference 2025](https://www.edr.state.fl.us/content/conferences/revenueimpact/archives/2025/_pdf/impact0710.pdf)
- [Virginia HB781 fiscal statement](https://lis.blob.core.windows.net/files/1141203.PDF)
- [Arkansas Issue 1](https://www.sos.arkansas.gov/uploads/elections/Issue_No._1_HJR_1018_of_2026_.pdf_.pdf)