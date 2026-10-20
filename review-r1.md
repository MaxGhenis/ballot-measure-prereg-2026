**MAJOR FIXES — not ready to freeze.**

The pooled estimator is algebraically correct, and the saved power calculations reproduce. The main problems are incomplete implementation, invalid handling of missing data, an unenforced confirmation rule, and fiscal assumptions that do not support the claimed refutation.

1. **[major] The registered late-count analysis cannot run.**  
   [REGISTRATION.md §4](/Users/maxghenis/reviews/policy-conditional-markets-2026-10/prereg-nov2026/REGISTRATION.md:62) specifies W2 through December 11 and intraday W3. [run_analysis.py](/Users/maxghenis/reviews/policy-conditional-markets-2026-10/prereg-nov2026/scripts/run_analysis.py:23) defines only W0 and W1; `--window W2` raises `KeyError`. Venue-average probabilities, RU-sign sensitivity and one-time-revenue sensitivity are also unimplemented.

   **Fix:** Implement these analyses before freezing, including W2’s November 6 eligibility screen and explicit treatment of qualitative one-time estimates. December 11 is an appropriate California endpoint: it is the Secretary of State’s certification deadline. The short primary window alone does not cover slow counts. [Official calendar](https://elections.cdn.sos.ca.gov/statewide-elections/2026-primary/election-guide/section-07-general-election-calendar.pdf)

2. **[major] The Novy-Marx–Rauh benchmark is not established as a lower bound for this estimand.**  
   The conversion to `−70/R_s` through `−150/R_s`, and its pooled weighting, are correct. But §6 omits that the published result concerns pension-asset losses in states in the lower half of credit quality. Gross annual tax receipts are not equivalent to an improvement in fiscal assets: revenue can fund required spending, and local earmarked receipts need not improve state credit. Fund-minus-national spreads also dilute an underlying state-bond response. [Published paper](https://www.aeaweb.org/articles?id=10.1257/pol.4.2.182)

   **Fix:** Present this as a conditional illustrative benchmark, or specify a defensible mapping from net fiscal resources to the observed fund spread. Remove the unconditional “lower bound” claim and restrict “refute” to the defined response, magnitude and window.

3. **[major] The category-N confirmation gate is ignored by the code.**  
   §6 requires primary β < 0, primary p < .05 **and** category-N p ≥ .05. [classify()](/Users/maxghenis/reviews/policy-conditional-markets-2026-10/prereg-nov2026/scripts/estimate.py:63) accepts no category-N result. `run_analysis.py:103` classifies before calculating N at lines 119–120. It can therefore report `CONFIRM` when H3 rejects.

   **Fix:** Calculate the control test first, enforce the complete decision rule, define what happens when H3 is unestimable, and test those cases.

4. **[major] H3 needs a valid control definition and a corrected registry.**  
   The unconditional N regression need not be zero under a genuine revenue effect. If N and revenue surprises correlate, then with `y = βX_R + e`, its slope contains `β·ΣX_NX_R/ΣX_N²`.

   Moreover, N currently includes fiscal or uncertain measures:

   - New Mexico Amendment 4: approximately $7.6 million in annual compensation costs. [Official fiscal report](https://www.nmlegis.gov/Sessions/26%20Regular/firs/HJR05.PDF)
   - Colorado Amendment 84: quantified state and county costs and possible fee increases. [Official statements, pp. 8–10](https://content.leg.colorado.gov/sites/default/files/2026-fiscal-impact-statements-english-accessible.pdf)
   - Arizona Proposition 144 and California Proposition 5: uncertain effects, rather than established immaterial effects.

   **Fix:** Freeze a quantitative materiality rule, recode fiscal and unknown cases, and test N conditional on revenue exposure—or use a justified control sample.

5. **[major] The documented capture sequence does not produce the analysis input.**  
   [RUNBOOK.md](/Users/maxghenis/reviews/policy-conditional-markets-2026-10/prereg-nov2026/RUNBOOK.md:21) runs market capture and asset capture separately, then analyzes the latest directory. [capture.py](/Users/maxghenis/reviews/policy-conditional-markets-2026-10/prereg-nov2026/scripts/capture.py:11) creates a different timestamped directory for each process. The analysis expects both kinds of files in one directory. Freeze step 0 also calls `capture.py assets` without tickers, capturing nothing.

   **Fix:** Provide one complete capture command or an explicit shared directory and manifest; derive tickers from the registry. Verify the actual runbook command sequence.

6. **[major] Missing data can change the sample silently or produce a false small p-value.**  
   Both Kalshi endpoint failures can become an apparently successful empty capture (`capture.py:43–50`). The analysis silently skips unavailable probability histories, while missing event prices survive into inference.

   Reproduced edge cases:

   - Zero exposure causes `pooled_test()` to crash when taking quantiles of an empty null.
   - NaN event prices produce β = NaN but p = `1/249 ≈ .004`.
   - `classify()` labels that result `WRONG SIGN`.

   **Fix:** Validate coverage, finiteness, identification and placebo length before inference. Persist failures and omissions; freeze a deterministic missing-data policy and return an explicit unestimable result.

7. **[major] Settlement probabilities are promised but never obtained.**  
   §3.1 promises settlement values after resolution. Capture obtains candles/history only; the analysis carries the last observed price forward. A final quote or trade at .97 need not become 1. The documented candle response supplies price observations. [Kalshi candle documentation](https://docs.kalshi.com/api-reference/market/get-market-candlesticks)

   **Fix:** Capture official resolution results and effective timestamps, and apply settlement values only from the appropriate time. Test histories ending short of 0 or 1.

8. **[minor] Power numbers are correct, but coverage and calibration need precise wording.**  
   Both saved 2,000-draw scenarios reproduce exactly:

   | Scenario | Median floor, bp/$bn | 10th–90th percentile | Share below conservative / upper benchmark |
   |---|---:|---:|---:|
   | Election night | 1.636 | 0.343–2.176 | 20.0% / 42.85% |
   | Slow count | 3.621 | 0.757–4.807 | 2.65% / 19.75% |

   However, [power.py](/Users/maxghenis/reviews/policy-conditional-markets-2026-10/prereg-nov2026/scripts/power.py:35) actually draws **five** measures; four pending California measures lack probabilities and are skipped, despite appearing in its nine-measure output list.

   Date-shift blocks are a reasonable event-window analogue of circular shifts. Their validity requires comparable historical and event-window errors; the +1 correction does not establish exchangeability. Planting negative effects of 2.8 SE across the 32 active-measure outcome combinations gives approximately **81.5% weighted rejection**, with individual outcomes around 74–88%.

   **Fix:** Correct the count and included-measure list, disclose assumptions, and call 2.8 SE approximate. Reconcile the empirical interval returned by `pooled_test()` with the normal interval used for refutation.

9. **[minor] The federal-election check cannot obtain its promised history.**  
   Capture requests two years of daily prices. It cannot supply November 9, 2022, and a November 2026 capture may lack the preceding close needed for November 6, 2024. The analysis silently omits unavailable comparisons.

   **Fix:** Archive sufficient fixed historical data and require both comparison returns.

10. **[major] Colorado’s fiscal exposures are not safely additive.**  
    The official analysis explicitly says Amendment 87’s receipts depend on whether Proposition 136 passes; Proposition 136 is currently an N placebo. NN and 137 also affect the same TABOR refunds: NN eliminates projected refunds, while 137 separately reduces them. Adding their standalone retained-receipt amounts appears to double-count overlapping refunds when both pass. This second conclusion is an inference from the official mechanisms. [Official statements, pp. 19, 26–27 and 63](https://content.leg.colorado.gov/sites/default/files/2026-fiscal-impact-statements-english-accessible.pdf)

    **Fix:** Freeze a joint fiscal payoff rule and necessary joint-probability assumptions, or exclude these interactions from the confirmatory exposure. Define F explicitly as receipts retained after refunds if NN and 137 remain R.

11. **[major] The inventory does not substantiate “every” market and measure.**  
    [enumerate_markets.py](/Users/maxghenis/reviews/policy-conditional-markets-2026-10/prereg-nov2026/scripts/enumerate_markets.py:24) excludes the unanchored substring `ital`, which matches legitimate “capital” and “hospital” titles. It also excludes “term limits” and accepts local Polymarket titles only with a state name or one of nine cities. Search failures can silently end enumeration.

    Separately, `measures.csv:151` combines San Francisco A–G into one row with different outcomes and fiscal effects.

    **Fix:** Preserve candidates and request-completion records, remove broad substring exclusions, reconcile against official ballots, and split A–G. A blocked freeze may honestly register a restricted snapshot, but cannot claim complete current enumeration. Align the runbook’s “freeze anyway” instruction with §9’s live-pull requirement.

12. **[major] Three states incorrectly fail the asset eligibility rule.**  
    `assets.csv` excludes Arkansas, Wisconsin and West Virginia because verified durations supposedly were not saved. Saved sponsor evidence contains September 30, 2026 effective durations of:

    | State | Fund | Duration |
    |---|---|---:|
    | Arkansas | MFARX | 7.56 years |
    | Wisconsin | WWTFX | 6.68 years |
    | West Virginia | MFWVX | 7.51 years |

    All meet the stated June 30 cutoff.

    **Fix:** Register them and regenerate dependent outputs, or document another consistent eligibility criterion. The durations for the **18 included states and their benchmarks match the saved documents**.

13. **[minor] Fiscal timing and horizons need completion.**  
    Eleven of thirteen R rows leave `F_first_year` blank. CA-P40’s 2027 refers to payment of the one-time tax, not an officially dated start for its recurring behavioral loss. SF-J’s $125 million is a **first-five-year annual average**, with substantial subsequent decline. Wyoming’s number excludes unestimated local effects.

    **Fix:** Populate timing, duration and coverage fields; distinguish unknown dates, temporary averages and incomplete totals.

14. **[major] The freeze establishes local content integrity, not an independently verifiable pre-election date.**  
    [freeze.sh](/Users/maxghenis/reviews/policy-conditional-markets-2026-10/prereg-nov2026/scripts/freeze.sh:9) creates checksums, a local commit/tag and a locally dated record. Those verify content against a retained hash. Without an independent timestamp or independently retained pre-election copy, the history and dates can be reconstructed later.

    **Fix:** Distinguish local freezing from timestamped registration. Before the deadline, preserve the commit/manifest hash through an independently timestamped mechanism, which may be private or embargoed. State the checksum exclusions accurately.

I checked **all 13 category-R rows**, plus five non-R classifications, against official materials:

| Measure | F, $bn/year | Source check |
|---|---:|---|
| CA-P3 | +10.000 | Correct midpoint of $5–15bn; extension from 2031. [LAO](https://lao.ca.gov/ballot/2026/prop3-110326.pdf) |
| CA-P40 | −0.500 | Follows the registered half-bound rule; recurring start unspecified. [LAO](https://lao.ca.gov/ballot/2026/prop40-110326.pdf) |
| CO-A87 | +1.972 | Correct FY2027–28 amount; interaction qualification needed. [Colorado](https://content.leg.colorado.gov/sites/default/files/2026-fiscal-impact-statements-english-accessible.pdf) |
| CO-NN | +0.521 | Correct retained receipts; new revenue is zero. Same source. |
| CO-137 | +0.175 | Correct retained-receipt amount; new revenue is zero. Same source. |
| WA-I645 | −3.892 | Correct SFY2031 amount; local revenue unchanged. [OFM](https://www.sos.wa.gov/sites/default/files/2026-07/FIS%20-%20Initiative%20645%20-%20FINAL.pdf) |
| WY-I1 | −0.0926 | Correct rounded state FY2028 loss; local loss unestimated. [SOS](https://sos.wyo.gov/Elections/Docs/2026/2026_Statewide_Ballot_Propositions.pdf) |
| FL-A2 | −0.031 | Correct recurring local loss from FY2027–28. [House analysis](https://www.flsenate.gov/Session/Bill/2025/1215/Analyses/h1215z.WMC.PDF) |
| FL-A3 | −11.835 | Correct rounded recurring benchmark of $11,834.7m. [REC](https://edr.state.fl.us/Content/conferences/revenueimpact/archives/2026F/_pdf/impact0710.pdf) |
| CA-RTM | +0.980 | Correct annual local estimate; 14-year term. [Official pamphlet](https://media.api.sf.gov/documents/N26_EN_VIP.pdf) |
| SF-H | +0.177 | Correct FY2027–28 estimate; indexed, 15 years. Same source. |
| SF-J | +0.125 | Correct midpoint; first-five-year average. Same source. |
| SF-I | −0.001 | Correct FY2027–28 recurring revenue loss. Same source. |

Verification included byte comparisons of 299 preregistration/memo files against `d497c6c`, source and caller inspection, official-source checks, saved fund-document comparisons, exact reproduction of both power scenarios, and in-memory estimator edge cases. The recorded test log reports eight passes; I did not rerun the fixture-writing suite. I found no advocacy for or against a measure, and the prose generally meets the requested voice. No files were changed and nobody was contacted.