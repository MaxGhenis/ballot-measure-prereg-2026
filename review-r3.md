# Round-3 review: November 3, 2026 ballot-measure pre-registration (commit `5f90279`)

## Verdict: MAJOR FIXES (one finding, about an hour's work)

Both round-2 majors are fixed as asked:
- **M1:** I re-derived the three Amendment 87 × Proposition 136 outcomes and the midpoint from the saved statement, and they match.
- **M2:** `registered_capture` and the deviation flag do what §5.4 says for fund bars.

One major gap is left. The capture rule looks only at Yahoo bars, never at market data. If the network block that §9 and the RUNBOOK expect happens during the Nov 6 capture, the registered reading is UNESTIMABLE. The real result would then come from a later capture picked after the election and logged as a deviation, which is the same problem M2 was meant to close. Once N1 is fixed I'd approve; the minor findings below don't need another full round.

I couldn't run code (read-only, no shell), so the tests and the power numbers were not re-executed. No files were changed and nobody was contacted.

## Round-diff

| # | Round-2 finding | Status | What I checked |
|---|---|---|---|
| M1 | A87 × 136 bounds | **Fixed** | See the derivation below. `interactions.csv` row 3 is `0.677, -0.619, 1.972`. §3.2 states the rule (midpoint of the range the possible outcomes span, ends as secondaries) and the arithmetic. 136 is RU with `F_sign` 0, so it adds nothing on its own, and `test_interaction_with_a_non_revenue_member` checks this pattern. There's a basis question in N4 (minor). |
| M2 | Registered capture, missing NAVs | **Fixed for fund bars; open for market data (N1)** | `REG_CAPTURE` stamps are right: DST ends Nov 1, so 9 p.m. EST = 02:00Z the next day. `registered_capture` takes the first complete capture at or after the opening stamp, or the first at or after the deadline. `deviation` is set whenever the capture used isn't the registered one, and a named run is flagged. Missing NAVs: the Oct 16 capture taken at 2:55 p.m. ET has the day's timestamp with `null` values, and `yahoo_daily` drops them, so a pre-NAV bar counts as missing, which is correct. Captures are moved to 9:30 p.m. Gaps remain in the dropping logic (N2) and in sealing the captures (N3). |
| m1 | Gate waived on any H3 failure | **Fixed** | `h3` is None only when `XN` is all zero (`run_analysis.py:359`). Any other non-OK H3 gives "unestimable", which blocks CONFIRM (`estimate.py:135-141`). |
| m2 | Settlement timing | **Fixed** | Kalshi uses `settlement_ts`, otherwise `close_time` only if it is at or before `retrieved`; "amended" is now in the status list. Polymarket uses `closedTime` only. Both are tested on real fixtures. |
| m3 | MA-Q8 | **Fixed** | §3.2 adds an explicit rule, and the −0.330 figure enters `F_secondary_bn`. |
| m4 | CO-132 | **Fixed, one leftover (nit)** | Coded O. But `F_annual_bn` is empty, so the O specification still leaves out its costs. |
| m5 | RU floor | **Fixed** | `F_sign` is 0 for A84, 136 and NE-441, with the reasons in the audit notes. |
| m6 | PolicyEngine specification | **Fixed** | `run_analysis.py:377`. |
| m7 | Interactions across specifications | **Fixed** | Revenue-share scaling at line 375; joint flag at lines 395-396. |
| m8 | Tests | **Fixed, two gaps** | The rewritten tests check what they claim. The deadline branch of `registered_capture` and a missing Nov 3 bar are still untested (N2). |
| m9 | `freeze.sh` reruns | **Fixed** | Stamps before committing, checks `power.json` inputs, skips steps already done, excludes `.hypothesis/`. |
| m10 | Uniqueness | **Fixed (disclosed)** | `integrity()` runs on every analysis; publishing is still Max's call. |
| m11 | Weak H3 | **Fixed** | `n_tax_limit` variant is reported and does not gate. |
| Nits | | **Fixed** | Manifest message, docstring, previous-trading-day check, 4 p.m. sampling. |

**M1 derivation, from `evidence/co/fis_A87_pp17-21.txt`:**
- **87 prevails:** $1,972.0 million in FY2027-28 (Table 1).
- **136 voids 87:** 0.
- **136 caps the top brackets at 4.4%:** two groups of taxpayers.
  - Below $510,834: 3.4 million × −$176 = −$598.4 million (line 147).
  - Above: 64,000 × −(0.7% × $25,000 + 0.2% × $75,000) = 64,000 × −$325 = −$20.8 million (Table 2).
  - Total −$619.2 million.
- **Midpoint:** (−0.619 + 1.972)/2 = 0.6765 → 0.677. ✓
- **Rule wording:** it reads well. Its scope is bounded because §3.2 lists the three outcomes, which keeps "possible resolutions" from being open-ended after the freeze.

## New findings

**N1 [major, code and text]. The registered capture ignores whether the market data was captured.**
- **Evidence:**
  - `registered_capture` (`run_analysis.py:255-264`) decides with `missing_bars` alone, which reads only Yahoo files.
  - If Kalshi or Polymarket is blocked during that capture, `capture.py` writes no market files, only manifest failures.
  - `market_probs` then returns "no capture file", every measure is omitted, `X` is all zero, `bench[0]` is None, and the reading is UNESTIMABLE.
  - Still, that capture is *the* registered one, because its fund bars are complete.
  - RUNBOOK lines 7–13 expect exactly this ("a later capture from an unblocked network can fill the gap; record that in `DEVIATIONS.md`"). §9 reports that this machine was blocked on Oct 16.
  - So the real result would come from a later capture chosen after the election, which is the fork M2 set out to close.
  - A partial block, with one venue down, is worse: it silently forces fallbacks or omissions in the registered reading.
- **Fix: register a market-completeness condition.**
  - The W1/W0 capture must have both of these for every measure with a freeze price, from at least one of its registered markets:
    - the history file (`kalshi_{m}_60m.json` / `pm_{token}_60m.json`);
    - the market record.
  - Fund bars and market files can come from different captures. Probabilities come from the first capture at or after the bar capture that satisfies the condition. The deadline is the Nov 13 capture, which is already scheduled; after that, omissions stand.
  - Code: add a `missing_markets(cap)` beside `missing_bars`, apply it in `registered_capture`, and record both capture paths in `res`.
  - Add one sentence to §5.4.
  - Change RUNBOOK lines 12–13 from "record in DEVIATIONS" to "rerun the capture; the rule picks it up".
  - Add a test with a capture that has every bar but is missing a market file.

**N2 [minor, code ≠ text]. In the deadline case, states are dropped by a different test than the registered one.**
- **Evidence:**
  - §5.4 says "every state still missing an event-day bar is dropped". The preflight checks Nov 3–6.
  - But `run()` drops a state only when its `y` contains a NaN (lines 337-340).
  - `panel.leg` takes differences over the bars that remain after `dropna()`. A fund missing its **Nov 3** bar therefore gets a finite two-day Nov 2→Nov 4 return on Nov 4. That return includes Election Day trading before the 4 p.m. baseline. The state is kept while `preflight_missing_bars` lists it.
  - A rank-1 ticker with **no file at all** makes `spreads_daily` raise `FileNotFoundError`, so the run crashes instead of dropping the state.
  - A W1 day missing from every series is quietly removed from `days` (lines 329-331), which shortens the window rather than dropping states or returning UNESTIMABLE.
- **Fix:**
  - Drop exactly the states in the preflight `missing_bars` result.
  - Make `spreads_daily` skip a missing file, and drop and list that state.
  - Return UNESTIMABLE if a registered W0/W1 day is missing everywhere.
  - Tests: a missing Nov 3 bar, a missing ticker file, and the deadline branch of `registered_capture`.

**N3 [minor, gaming after the freeze]. Capture directories aren't sealed when they're made.**
- **Evidence:**
  - Rule inputs: the "first capture" is picked from whatever directories exist when the analysis runs.
  - Overwriting a capture: `capture.py --dir data/raw/capture/<stamp>` writes into an existing directory and merges its manifest, so the registered capture can be overwritten and keep its name.
  - Deleting a capture: deleting a directory changes which one comes first.
  - No seal: nothing commits or timestamps a capture when it is taken. RUNBOOK commits only at step 3.
- **Fix:**
  - RUNBOOK step 2: after each capture, `git add data/raw/capture/<stamp> && git commit`, and `ots stamp` its `manifest.json`.
  - `registered_capture`: skip any directory whose manifest `stamp` differs from its name or whose `commands` list has more than one entry.
  - Record the chosen manifest's sha256 in `res`.

**N4 [minor, judgment; text]. The −0.619 outcome counts gross revenue; the rest of Colorado counts retained revenue.**
- **Evidence:**
  - The registry scores Colorado on receipts the state keeps: NN, 137, and 132, whose note says "Gross receipts are refundable under forecast TABOR conditions".
  - A87's $1.972 billion is retained because it is "exempt from TABOR as a voter-approved revenue change". A cut from the surviving 3.7%/4.2% brackets would not be exempt in that way. With refunds of $521 million forecast for FY2027-28, it would mostly reduce refunds: the retained loss is about −$0.10 billion if NN fails, and −$0.62 billion only if NN passes.
  - On a retained basis with NN failing, the midpoint would be about 0.94, not 0.677.
  - The registered bounds still bracket both, so this is not a repeat of M1.
  - **Smaller point:** −0.619 is a tax-year-2027 figure set against a FY2027-28 figure for A87, roughly 2% off.
- **Fix (pick one before the freeze):**
  - Add to §3.2 that the cap outcome is scored as the gross revenue change, a simplification that ignores the TABOR offset and the three-way interaction with NN.
  - Or score it as retained revenue with NN failing (−0.098, midpoint 0.937), and keep −0.619 as the low bound.

**Nits**
- **CO-132:** `F_annual_bn` is empty, so the O specification still leaves out its costs. Set it to −0.0089 (FY2027-28), or note the omission.
- **`integrity()` coverage:**
  - It doesn't check `evidence/`, although `census/stc_2025_total_taxes.json` sets the benchmark and `history/` feeds the federal check.
  - It ignores files added to `scripts/` after the freeze.
  - Fix: check every path in SHA256SUMS outside `data/raw/capture/` and `results/`, and list any file not in the sums.
- **One malformed capture blocks every run:** `run()` always calls `registered_capture`, even when a capture is named. `missing_bars` doesn't catch `TypeError` from a malformed chart JSON. Catch `Exception` there and list the directory as skipped.
- **W2 capture timing:** §5.4 refers to "the first capture after 9 p.m. on December 11", but none is scheduled for December 11–13. The December 14 capture is then the deadline capture, which is harmless; scheduling one capture on December 11 would make the text literal.

## Checked and found sound
- The pre-NAV Yahoo bar is null and is dropped, so it counts as missing; there's no stale-NAV risk.
- The UTC stamps match 9 p.m. EST in every window.
- `classify`'s handling of the gate matches §6.
- In `freeze.sh`, `set -o pipefail` with `tee` makes a failing test abort the freeze, and the check on `power.json` inputs covers the registry files and the spread panel.
- The A84, 136 and 441 RU sign is 0, with reasons recorded.