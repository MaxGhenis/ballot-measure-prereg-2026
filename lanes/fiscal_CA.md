# Lane brief: official ballot lists and fiscal estimates for November 3, 2026 measures (CA)

Read `lanes/_common.md` first; its rules apply.

**Input.** `data/derived/measure_markets.csv` lists every Kalshi or Polymarket market found on a U.S. state or local ballot measure that closes on or after November 3, 2026. Kalshi rows come from an October 11 snapshot and Polymarket rows from October 16. Columns: state, venue, market id, the market's measure code (Kalshi), label, volume and quotes. Your states: California only (CA). Include the San Francisco, Bay Area regional and Los Angeles measures if any appear in the input.

**Task, for each of your states:**

1. **Official list.** From the secretary of state or election office, list every statewide measure on the November 3, 2026 ballot: official number or letter, official ballot title, and type (constitutional amendment, initiative, referendum, bond question, advisory). Note any measure that was withdrawn, struck from the ballot, or retitled by a court, with the date.
2. **Market mapping.** Map each market row in the input to its official measure. A market with no matching measure on the official list is flagged NOT ON BALLOT. A measure with no market gets a row marked "no market".
3. **Fiscal estimate,** for every measure that changes state or local taxes, fees, revenue, borrowing or required spending, from the official fiscal analysis (voter-guide fiscal impact statement, legislative fiscal note, revenue estimating conference, or bond act text):
   - the annual change in state revenue and in local revenue, in dollars, if the measure passes;
   - whether the change is recurring or one-time, and the first fiscal year it applies;
   - for bonds, the principal authorized and the estimated annual debt service;
   - the source's own words for any range or "unknown".
   Do not compute estimates yourself. If the official analysis gives none, write "none published". Mark the sign (+ = more revenue or borrowing capacity for the state or locality).
4. **Bond-relevant provisions.** Flag any measure that directly changes the tax treatment of municipal bond interest, debt limits, the pledge or security for existing bonds, or limits on property tax levies used for debt service, with a quote.
5. **Local measures.** For any local (county or city) measure in the input, give the local election office's official listing and the local fiscal analysis, if any.

**Output tables:** (a) official measure list per state, with market ids mapped; (b) fiscal estimates (state, measure, annual state revenue change, annual local revenue change, recurring or one-time, first fiscal year, bond principal and debt service, source URL, quote); (c) bond-relevant provisions; (d) gaps and UNVERIFIED items.
