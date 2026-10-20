# Pre-registration: do ballot-measure odds move state municipal bond prices? November 3, 2026

*Max Ghenis · registered before the November 3, 2026 election · version 1 (frozen)*

The freeze commit, its sha256 sums and the independent timestamp are recorded in `FREEZE.md`. Any change after the freeze goes to `DEVIATIONS.md` with a date and a reason.

## 1. Question

When the passage odds of a state or local ballot measure move on election night and the count days that follow, does the state's municipal bond spread move with them, by an amount that scales with the measure's official fiscal estimate?

An October 2026 study of the same question (`../memo.md`) found nothing detectable for California's Proposition 40 over its whole campaign: +0.8 basis points (SE 2.2) per full swing in Kalshi's odds, against 6.4 to 6.9 basis points, the effect a 5% test finds four times in five, depending on its direction. Election night concentrates the news. Many measures resolve together, and their surprises differ in size and sign, so a pooled test across measures can reach a lower floor than any single campaign regression.

## 2. Hypotheses

- **H1 (primary, pooled).** Across states with a testable spread, the state-minus-benchmark yield spread falls when the expected annual revenue from the state's revenue measures rises: β < 0 in the pooled model of section 5.1, where β is in basis points per $1 billion a year of state and local revenue.
- **H2 (per measure).** For each revenue measure with a testable spread, the spread moves against the measure's passage probability with the sign of its fiscal estimate (section 5.2).
- **H3 (placebo set).** Measures with no material fiscal effect (category N) show no relation to the spread, conditional on revenue exposure: β_N = 0 (section 5.3).
- **H4 (bonds, secondary).** Bond authorizations (category B) raise the spread in proportion to their annual debt service.

The credit channel predicts the sign in H1 and H2: more revenue lowers expected default risk and lowers yields. A second channel, the in-state tax exemption, can push the same way for income tax increases on residents who hold in-state bonds. The registration takes no view on any measure.

## 3. Data

### 3.1 Measures and markets

- **Inclusion rule.** Every Kalshi or Polymarket binary market on the passage of a U.S. statewide or local measure decided on November 3, 2026, listed in `registry/markets.csv` at the freeze. `scripts/enumerate_markets.py` builds the list from each venue's public API and saves every candidate it considered, with the decision and the reason (`data/derived/enumeration_candidates.csv`), and every request that failed (`data/derived/enumeration_meta.json`). Markets listed after the freeze are reported but stay out of the primary test.
- **What the enumeration covers.** The final enumeration ran live on October 19, 2026 (`enumeration_meta.json`): it scanned 15,195 Kalshi series and kept 240 markets from 133 candidate series, and scanned 3,663 open Polymarket events and kept 39 markets, with no failed request. Polymarket's Gamma API stops paging at an offset of about 2,000, so `scripts/sweep_polymarket_end_dates.py` also read every open Polymarket event ending between November 2, 2026 and January 31, 2027, splitting the period until each window was read in full; it found no U.S. ballot-measure market the enumeration had missed (`data/derived/polymarket_end_date_sweep.json`). The registration claims the markets listed at the freeze, not markets listed afterward.
- **Pending series.** Some measures sat in Kalshi series that the memo's October 11 snapshot did not capture. The live pulls of October 16 and 19 replaced every `pending-series:` entry with the series' markets, matched by label; none remains.
- **Official list.** `registry/measures.csv` maps each market to the measure on the official ballot list (secretary of state or election office), one row per measure. A market with no official measure is dropped and reported.
- **Registry.** `registry/SUMMARY.md` (built by `scripts/summarize_registry.py`) counts the registered measures by state and category and lists every revenue measure. The official lists, fiscal estimates and quotes come from research lanes that read election offices, fiscal offices and measure texts (`lanes/out-fiscal_*.md`, audited under the materiality rule in `lanes/out-audit_*.md`), and California's from the LAO analyses saved in `evidence/ca/`. Where a Kalshi ticker's code conflicts with the official numbering (Georgia, Rhode Island, Wisconsin), the market maps by its label, which matches the official title.
- **Primary market and freeze price.** For a measure with several markets, the primary market is the one with the most volume at the freeze snapshot (`registry/prices_at_freeze.csv`, built by `scripts/freeze_prices.py`). Its freeze price is the bid-ask midpoint when there is an ask above 0 and the spread is 10 cents or less, otherwise the last trade (a bid and an ask both at 0 is no quote). A market that has never traded reports a last price of 0, which is not a price: without such a quote, the measure has no freeze price, is listed in `registry/unpriced_at_freeze.csv`, and stays out of every test. The average of the probabilities of every market that covers the window is a secondary specification.
- **Probability series.** For Kalshi, the hourly candle's bid-ask midpoint when there is an ask above 0 and the spread is 10 cents or less, otherwise the last trade, carried forward. For Polymarket, the last CLOB price at or before the sampling time. Daily values are taken at 4 p.m. Eastern, when the funds strike their closing prices and net asset values.
- **Settlement.** Once a market has resolved, its probability from the resolution time on is the settlement value from the market record captured with the prices: for Kalshi, the result with the settlement time, or, without one, the market's close time if it had passed when the record was captured (Kalshi rewrites the close time when it closes a market early; a scheduled close in the future says nothing about resolution); for Polymarket, the outcome prices with the closed time only (its end dates can come before resolution). A last trade at 0.97 does not stand in for a settled 1. `tests/` checks both rules on saved records of resolved markets.
- **Missing prices.** If the primary market has no price at a sampling time, the measure's other registered markets are tried in order of volume at enumeration, and the market used is recorded. If no market covers every sampling time, the measure is omitted from that window and listed with the reason. Every capture failure is recorded in the capture's `manifest.json` and reported with the results.

### 3.2 Fiscal estimates and categories

F_i is the official estimate of the annual change in state plus local revenue if measure i passes, in $ billion, positive for more revenue. It comes from the official fiscal analysis named in `registry/measures.csv`, which also quotes it.

**Categories (the materiality rule).**
- **R**: the official analysis gives a number for the change in state or local revenue (taxes, fees, or receipts retained under a revenue limit).
- **RU**: revenue changes but the analysis gives no number, or calls the effect unknown, indeterminate or potential. `F_sign` records the expected sign where the analysis or text makes it clear; it is 0 when the analysis bounds the effect below $10 million a year or when the measure's effect enters through an interaction. Current receipts that a measure would end, stated without a forecast of the change, do not make it R: the measure stays RU and those receipts enter a secondary specification (`F_secondary_bn`; Massachusetts Question 8, −$0.330 billion). Receipts that are refunded under a revenue limit are not retained revenue (Colorado Proposition 132 is coded O for its costs).
- **B**: a bond authorization, with its principal and official annual debt service.
- **O**: any other fiscal effect of $10 million a year or more (costs, spending mandates, transfers, earmarks of existing revenue), or a cost described as unknown or potentially significant.
- **N**: the official analysis states no fiscal effect, a minimal, negligible or no significant effect, or a quantified total below $10 million a year with no unquantified component. Without an official analysis, a measure whose text could change revenue or spending by $10 million a year or more is RU or O.

**Rules for F.**
- **Ranges** take the midpoint ("$5 billion to $15 billion" gives 10).
- **"Less than $X"** gives X/2, with the stated sign.
- **Recurring estimates** use the first full fiscal year at full effect, or the official recurring benchmark when one is stated (for example, Florida's figure at full effect). `F_first_year`, `F_horizon` and `F_coverage` record the year, how long the change lasts (a temporary average is marked as such) and whether local effects are estimated.
- **One-time revenue** stays out of the primary test and enters a secondary specification spread evenly over the years the official estimate names, or over three years when it names none. A qualitative amount takes the smallest number the phrase allows: "tens of billions" is $20 billion.
- **Bond authorizations** enter H4 through their official annual debt service and stay out of H1.
- **Costs and spending mandates** (O) enter a secondary specification as negative revenue (`F_secondary_bn`): the recurring annual cost the official analysis states, under the rules above (range midpoint; for a cost the analysis says keeps growing, the latest year it states; "tens of millions" is $20 million, the smallest amount the phrase allows). Costs below $10 million a year enter at zero, as do one-time costs, transfers or earmarks of existing receipts, and costs the analysis cannot quantify. Five O measures have such a figure: Colorado Proposition 132 (−$0.068 billion by year five, the Blue Book's latest stated year), North Dakota Measure 2 (−$0.065 billion), San Francisco C (−$0.060 billion by FY2034-35), Michigan Proposal 26-1 (−$0.022 billion) and California Proposition 39 (−$0.020 billion).

**Interactions.** When an official analysis says one measure's revenue depends on another's passage, or two measures draw on the same receipts, `registry/interactions.csv` records the pair with the official text. Expected revenue then adds p_i·p_j·(F_joint − F_i − F_j) for the pair (section 5.1), where a member outside category R counts as F = 0 on its own. F_joint comes from official figures; when the analysis leaves it to how a legal conflict resolves, F_joint is the midpoint of the range the possible resolutions span, computed from official figures, and the ends of that range enter secondary specifications. Two pairs are quantified. Colorado's Proposition NN and Proposition 137 draw on the same TABOR refunds; if both pass, the state retains $0.521 billion in FY2027-28, NN's total (an overlap rule built from the official figures, `lanes/out-audit_WEST.md`). Colorado's Amendment 87 raises $1.972 billion alone, but if Proposition 136 also passes, receipts depend "upon the resolution of this conflict". Amendment 87 may prevail ($1.972 billion); Proposition 136 may void it ($0); or Proposition 136 may cap only the brackets above $500,000 at 4.4%, leaving Amendment 87's 3.7% and 4.2% brackets as a tax cut. From the official taxpayer figures (3.4 million taxpayers saving $176 on average, and 64,000 above $510,834 who would save $325 each on their first $100,000; tax year 2027), that last outcome loses about $0.619 billion. The range is −$0.619 billion to $1.972 billion, registered at its midpoint, $0.677 billion (`evidence/co/fis_A87_pp17-21.txt`). Two simplifications are disclosed. First, −$0.619 billion is the gross change in revenue. Colorado's other rows count receipts the state retains, and a cut from the 3.7% and 4.2% brackets is not exempt from TABOR the way Amendment 87's increase is: if Proposition NN fails, the cut mostly reduces the $521.0 million of TABOR refunds forecast for FY2027-28 under current law (Proposition NN's statement), leaving about −$0.098 billion retained, and if NN passes, about −$0.619 billion. Over the possible resolutions of both measures the range is the same, −$0.619 billion to $1.972 billion, so the registered midpoint does not change; the three-way interaction with NN is not modeled beyond this. Second, −$0.619 billion is a tax-year 2027 figure set against Amendment 87's FY2027-28 figure, a difference of about 2%. Pairs whose joint effect the analyses leave unquantified are listed with an empty F_joint, enter additively, and flag their per-measure estimates.

**PolicyEngine.** Where policyengine-us models a measure, its static estimate is recorded next to the official one (`pe/api/`): California Proposition 3 (`scripts/pe_runs.py`, tax year 2031) and Washington I-645 (the memo's policy 98675). It enters a secondary specification. The primary test uses official estimates only.

### 3.3 Assets

`registry/assets.csv` names one instrument for every state with a registered measure, and New York, the memo's second state. The order of preference:

1. a state-specific municipal ETF with prices on every placebo day, against iShares' national ETF (MUB). California (CMF) and New York (NYF) qualify. Franklin's state ETFs, converted from mutual funds in October and November 2025, lack a full placebo window;
2. otherwise, a state-specific open-end municipal fund's daily net asset value, against the Franklin Federal Tax-Free Income Fund (FKTIX, a national fund). Where Franklin runs a fund for the state, that fund is used, so both legs share a sponsor and its pricing.

A state qualifies only when its fund's sponsor publishes an effective duration dated June 30, 2026 or later, saved in `evidence/funds/`. Closed-end funds do not enter: their prices carry leverage and discounts to net asset value. The state search is `lanes/out-assets.md`, which found 275 state-specific funds in 34 states.

Twenty-one states are testable: California and New York (tier 1), and Alabama, Arizona, Arkansas, Colorado, Georgia, Kansas, Louisiana, Maryland, Massachusetts, Michigan, Minnesota, Missouri, Nebraska, New Mexico, North Carolina, Ohio, Virginia, West Virginia and Wisconsin (tier 2). Every other state with a registered measure is listed as untestable, with the reason. Florida, Washington and Wyoming have revenue measures and no state-specific fund. Daily returns come from adjusted closes (Yahoo Finance chart service; `scripts/capture.py`). The spread change on day t is −(r_state/D_state − r_bench/D_bench) × 100 basis points. Fund spreads dilute a state-bond response: a fund holds other assets and the benchmark holds some of the state's bonds.

### 3.4 Placebo days

The 250 trading days ending October 30, 2026, minus November 5 to 7, 2025 (after the November 4, 2025 election). The same days serve every state, so cross-state correlation and fat tails carry into the null (`scripts/panel.py`). The power analysis at the freeze uses the 250 trading days ending at the freeze capture; the analysis uses the days ending October 30.

## 4. Event windows

- **Primary window (W1).** The three trading days November 4, 5 and 6, 2026, each a close-to-close return paired with that day's change in expected revenue. A measure called on election night contributes mostly through November 4.
- **W0.** November 4 alone (secondary).
- **W2 (late count).** Every trading day from November 9 through December 11, 2026 (California's certification deadline), for measures whose primary market is between 0.05 and 0.95 at the November 6 close; other measures enter with no change (secondary). California counts slowly, so its close measures resolve here.
- **W3 (intraday, ETF states only).** From the last 5-minute bar at or before 3:55 p.m. Eastern on November 3 to the bar ending at 10:30 a.m. on November 4, with probabilities sampled at the same times. Its placebos are the same clock window on every earlier pair of trading days in the 5-minute capture (about 40); it runs only with at least 30 (secondary).

## 5. Tests

### 5.1 Pooled test (primary)

- **Exposure.** E_s(t) = Σ_i p_i(t)·F_i + Σ_pairs p_i(t)·p_j(t)·(F_joint − F_i − F_j) over category R measures in state s, the expected annual revenue change, treating outcomes in different markets as independent. X[s, t] = E_s(t) − E_s(t − 1). Without interactions, X[s, t] = Σ_i dp[i, t]·F_i.
- **Model.** y[s, t] = β·X[s, t] + e[s, t], with y the spread change in basis points. States with a testable spread and no revenue measure enter with X = 0. A secondary version adds day intercepts.
- **Inference.** Date-shift placebos (`scripts/estimate.py`). X stays fixed, and y is replaced by the spread changes on each block of T consecutive placebo days, the same days for every state. The placebo standard error is the standard deviation of β across blocks; the p-value is the share of blocks with |β| at least as large as the actual |β|, with the +1 correction; the 95% interval is the placebo interval, β minus the 97.5th and 2.5th percentiles of the placebo βs. This carries the memo's circular-shift logic over to an event window. It assumes that the spreads' errors in the event window resemble those on placebo days; the federal-election check in section 5.4 measures how far election days depart from that. The smallest detectable effect is reported as about 2.8 × the placebo SE, which assumes the placebo βs are close to normal.
- **Second scaling (secondary).** X'[s, t] uses F_i / R_s × 100, where R_s is state tax revenue in FY2025 (Census Annual Survey of State Government Tax Collections). β' is then in basis points per 1% of state revenue.

### 5.2 Per-measure tests

For each R, RU or B measure i in state s: b_i = Σ_t y[s, t]·dp[i, t] / Σ_t dp[i, t]², in basis points per full swing, with date-shift placebos on state s's spread. b_i is also reported per $ billion (b_i / F_i). When another fiscal measure in the same state moves by 0.10 or more in the same window, or the pair is listed in `registry/interactions.csv`, b_i is flagged as joint.

### 5.3 The placebo set and the other specifications

- **H3.** y[s, t] = β_R·X[s, t] + β_N·X_N[s, t] + e, where X_N sums the probability changes of category N measures (F = 1), with date-shift placebos for both coefficients. Conditioning on revenue exposure keeps a correlation between placebo-set and revenue surprises from producing a spurious β_N. With no revenue exposure the model is β_N alone. H3 is computed before the primary reading, which uses it as a gate (section 6). If no category N measure moves, H3 is untestable and the reading says so. If N measures move but H3 cannot be estimated for any other reason, the gate is unestimable and blocks a confirmation. A version of H3 without the tax-limit N measures (`n_tax_limit`: Arizona Proposition 141, Louisiana Amendment 1, North Carolina's 3.5% cap, Utah Amendment B) is reported beside it and does not gate.
- **H4.** The pooled model with X built from category B measures' annual debt service.
- **Secondary specifications**, each reported whatever its sign: day intercepts; the revenue-share scaling (the primary exposure, interactions included, divided by state tax revenue); adding category O's stated recurring costs as negative revenue; PolicyEngine's F where it exists and the official F otherwise, with the interactions; the venue average of probabilities; adding RU measures with F = F_sign × the median |F| of the registered R measures; adding one-time revenue spread over its years; adding RU measures' stated receipts (`F_secondary_bn`); the interactions at their lower and upper bounds; and no interactions.

### 5.4 Validity, missing data and the federal-election check

- Every estimate is computed only from finite inputs, with some exposure and at least 100 placebo blocks (30 for W3). Otherwise it is reported as UNESTIMABLE with the reason, never as a number.
- Measures omitted for missing prices, fallbacks to a secondary market and capture failures are listed with every result.
- **Registered capture.** W0 and W1 use the first capture stamped after 9 p.m. Eastern on November 6 in which every rank-1 instrument has daily bars for November 3 to 6. If none has them by the capture after 9 p.m. Eastern on November 9, that capture is used and every state still missing an event-day bar is dropped and listed. W3 uses the first capture after 9 p.m. Eastern on November 4 with 5-minute bars for November 3 and 4 (deadline: the capture after 9 p.m. on November 6). W2 uses the first capture after 9 p.m. Eastern on December 11 with daily bars for every W2 day (deadline: after 9 p.m. on December 14); the W2 days are fixed in advance as the NYSE trading days from November 9 to December 11 without Thanksgiving (24 days; fund values post on Veterans Day and on the day after Thanksgiving), with the November 6 close as the baseline. Fund net asset values for a day appear on Yahoo after about 6:30 p.m. Eastern. The states dropped are exactly those the preflight lists, including a state whose price file is missing; if a registered day of W0, W1 or W2, or the window's baseline close (November 3; November 6 for W2), is missing from every series, the window is UNESTIMABLE. Market data (probabilities and settlement records) come from the first capture at or after the bar capture in which every measure with a freeze price has, from at least one of its registered markets, the market record and the 60-minute price history, or the venue's recorded answer that there is none; the deadline is the capture after 9 p.m. Eastern on November 13 (W2: December 14), after which omissions stand. Fund bars and market data can therefore come from different captures, and both are recorded. Only sealed captures count. A capture is sealed when its manifest names it, records one capture command, started within an hour of its stamp and lists exactly the files present with their sha256; when the manifest carries an OpenTimestamps receipt for its bytes; and when the directory is committed with no later change. `scripts/seal_capture.sh` seals each capture as soon as it is taken; if the timestamp fails, the capture does not count until the script is rerun on it. The rule lists every capture it skips, with the reason. `scripts/run_analysis.py` picks the registered captures itself, lists missing bars and market data before estimating, records the sha256 of each capture's manifest, and records any run on another capture as a deviation.
- **Integrity.** Every run checks every file in `SHA256SUMS` outside `data/raw/capture/` and `results/` (the registry, scripts, evidence and tests), records any mismatch with the result, and lists files in those folders that the sums do not cover.
- The spread changes on November 6, 2024 and November 9, 2022, the trading days after the last two federal elections, are compared with the placebo distribution, from five years of daily prices archived at the freeze (`evidence/history/`). A day counts only when the archive has that day and the previous trading day.

## 6. What counts as confirming or refuting

The benchmark is illustrative. Novy-Marx and Rauh (2012) found that, for states in the lower half of credit quality, spreads rose 7 to 15 basis points for each 10% of state-generated revenue lost to pension-asset losses. For a state with tax revenue R_s ($ billion), that maps to β_s = −70/R_s to −150/R_s basis points per $ billion of annual revenue, and the pooled benchmark averages β_s with weights Σ_t X[s, t]². The mapping assumes that a change in annual tax receipts moves credit as much as a loss of the same size in assets would. Receipts can fund required or earmarked spending, local receipts need not improve state credit, a recurring change is worth more than a one-time one, and fund spreads dilute a state-bond response. The benchmark therefore gives a scale for reading the estimate, not a prediction.

- **Unestimable.** The primary test cannot be computed (section 5.4); the reason is reported.
- **Confirm.** β < 0 with placebo p < 0.05, and the placebo-set gate passes: H3's β_N has p ≥ 0.05, or H3 is untestable because no category N measure moved (reported as such).
- **Inconclusive** when β < 0 with p < 0.05 but H3 also rejects, since the placebo set moving too means something other than revenue may move the spreads; or when N measures moved but H3 could not be estimated.
- **Wrong sign.** β > 0 with p < 0.05. Reported as an anomaly, never as support.
- **Refute.** p ≥ 0.05, and the placebo 95% interval lies entirely above the benchmark at its conservative end. That rules out, for the measures and window tested, a response in these fund spreads as large as the benchmark's mapping implies. It does not rule out effects that work through channels the mapping omits. If the interval excludes only the 15 bp end, the result rules out the upper end alone.
- **Inconclusive.** Anything else. The power analysis (section 7) shows this is the likeliest outcome unless large fiscal measures surprise.

`classify()` in `scripts/estimate.py` implements these rules, and `tests/test_estimate.py` checks it, including the gate and the unestimable cases.

## 7. Power

`scripts/power.py` simulates each revenue measure with a freeze price passing with probability equal to that price, takes probability moves equal to the surprise (with the registered interactions), and computes the smallest detectable β for each draw. `results/power.json` holds the numbers, the measures drawn and the measures left out for lack of a freeze price; `scripts/fill_power_summary.py` writes the paragraph below from it. <!-- power-summary:start -->With 2,000 simulated outcomes of the 7 measures drawn (CA-P3, CA-P40, CO-Amendment87, CO-PropositionNN, CO-Proposition136, CO-Proposition137, CA-local-RTM: every revenue measure with a freeze price in a testable state, plus measures that enter only through a registered interaction), and every surprise realized on election night (scenario A), the median smallest detectable β is 2.0 basis points per $1 billion a year (10th to 90th percentile, 1.0 to 5.9). The benchmark's median is −0.48 at its conservative end and −1.02 at its upper end. The smallest detectable β falls below the benchmark's size in 4% of simulated outcomes at the conservative end and 22% at the upper end. If only 60% of each surprise is realized by November 6 (scenario B, a slow count), the median rises to 4.3, and those shares are 3% and 4%. The panel has 250 placebo days; 3 revenue measures in testable states lack a freeze price.<!-- power-summary:end -->

## 8. Data capture and timetable

| When (Eastern) | What |
|---|---|
| Before the freeze (by October 29) | Final enumeration and prices (`scripts/enumerate_markets.py`, `scripts/freeze_prices.py`); `scripts/capture.py all`; panel and power; freeze (`scripts/freeze.sh`) |
| November 3, before 4 p.m. | `scripts/capture.py all`: last pre-election snapshot of every registered market and fund |
| November 4 and November 6, after 9 p.m. | `scripts/capture.py all` (fund net asset values post after about 6:30 p.m.), then `scripts/seal_capture.sh`, as after every capture below |
| November 6 | Primary analysis (W1), W0 and W3, and the write-up, whatever the result |
| November 9, after 9 p.m. | `scripts/capture.py all`, the W1 deadline capture, if any bar was still missing |
| November 13, after 9 p.m. | `scripts/capture.py all`, the deadline capture for market data in W0, W1 and W3 |
| December 11 and December 14, after 9 p.m. | `scripts/capture.py all`; W2 after California's certification (December 14 is the W2 deadline capture) |

`RUNBOOK.md` gives the commands. Kalshi's and Polymarket's histories stay available through their APIs after settlement. Yahoo keeps 5-minute bars for about 60 days, inside the timetable.

## 9. Known limits

- On October 16 this machine's network blocked kalshi.com, Kalshi's API, Polymarket's CLOB and both venues' documentation (a certificate from "NetAlerts Services" replaced the sites' own). The block lifted that evening; the final enumeration, freeze prices and freeze capture were pulled live on October 19. The election-week captures need an unblocked network for both venues' prices; if one is blocked, the registered rule (section 5.4) takes market data from the first later capture that has them, up to November 13.
- Florida, Washington and Wyoming have revenue measures and no state-specific fund, so the primary test covers the revenue measures of the testable states only. `registry/assets.csv` gives every state's status.
- Tier 2 spreads use net asset values, which rest on a pricing service's evaluated prices and may lag trades in thinly traded bonds.
- Independent measurement error in the probabilities tends to pull slopes toward zero, and thin markets add more. The primary-market rule and the settlement values limit it.
- Expected revenue treats outcomes in different markets as independent.
- Election days also carry federal news. State-minus-benchmark spreads net out common moves; the check in section 5.4 measures what is left.

## 10. Files and freeze

- `registry/` holds the registered measures, markets, interactions, assets, freeze prices and state codes.
- `scripts/` holds the enumeration and its Polymarket coverage sweep, the capture and its seal, the panel, estimators, power, analysis and PolicyEngine runs.
- `tests/` holds the estimator and end-to-end tests (synthetic data only).
- `evidence/` holds official ballot lists, fiscal analyses, Census revenue, fund documents and the archived price histories.
- `lanes/` holds the research briefs and outputs.
- `scripts/freeze.sh` checks that `results/power.json` was computed from the files being frozen, writes `SHA256SUMS` (every file except caches), timestamps it with OpenTimestamps (`SHA256SUMS.ots`; only a salted hash leaves the machine) before committing, then commits and tags the freeze. It is safe to rerun. `FREEZE.md` records the hashes, the commit and how to verify them. The timestamp proves the registration existed by then, not that it was the only one; publishing it is Max's call.
