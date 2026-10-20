# Fiscal-category audit for the November 3, 2026 ballot-measure pre-registration

You are a research lane. Your sandbox is read-only: put your whole result in your final message. Do not contact anyone, post, or submit anything. Use official sources only: the state's (or locality's) official fiscal note, fiscal impact statement, voter guide or legislative fiscal analysis, the secretary of state's ballot list, and the measure text. Never rely on news or advocacy sites for a fiscal number. Quote verbatim and give the URL and page for every number and every classification.

**Context.** A pre-registered study (folder `prereg-nov2026/`, see `REGISTRATION.md` sections 3.2 and 5) tests whether ballot-measure passage odds move state municipal bond spreads, scaling each measure by its official estimate of the annual change in state plus local revenue. Category N is the placebo set and must contain only measures with no material fiscal effect. An independent review found the N category unreliable: 83 of 87 N rows carry no fiscal quote, Colorado's Proposition 136 ("Income Tax Rate Limit") is coded N, New Mexico Amendment 4 has about $7.6 million a year of compensation costs, Colorado Amendment 84 has quantified costs, and Arizona Proposition 144 and California Proposition 5 have uncertain effects.

**The materiality rule (apply it exactly).**
- **R**: the official analysis gives a number for the change in state or local revenue (taxes, fees, or retained receipts under a revenue limit). F = the annual amount in $ billion, positive for more revenue, using: the midpoint of a stated range; X/2 for "less than X"; the first full fiscal year at full effect, or the official recurring benchmark if one is stated.
- **RU**: the analysis says revenue changes but gives no number, or calls the revenue effect unknown, indeterminate, potential or dependent on future decisions. Give the expected sign (+1 more revenue, −1 less) if the analysis or text makes it clear, else 0.
- **B**: a bond authorization. Give the principal and the official annual debt service if stated.
- **O**: any other quantified or stated fiscal effect of $10 million a year or more (costs, spending mandates, transfers, earmarks of existing revenue), or a cost described as unknown or potentially significant.
- **N**: the official analysis states no fiscal effect, a "minimal", "negligible" or "no significant" effect, or a quantified total effect below $10 million a year with no unquantified component. If no official fiscal analysis exists, classify from the measure text and say so; when the text could plausibly change revenue or spending by $10 million a year or more, use RU or O, not N.

**For every row in your list** (the CSV named in your lane brief), return one row of a CSV block with these columns:
`measure_id,new_category,F_annual_bn,F_sign,F_first_year,F_horizon,F_coverage,onetime_bn,onetime_years,debt_service_bn_per_year,fiscal_quote,fiscal_source,notes`
- `F_first_year`: the fiscal year of the F figure (e.g. "FY2027-28"); `F_horizon`: "permanent", "N years" or "not stated"; `F_coverage`: "state", "local", "state+local", or e.g. "state; local not estimated".
- `onetime_bn`, `onetime_years`: one-time revenue and the years it spans, if any (write the phrase if the official figure is qualitative, e.g. "tens of billions").
- `fiscal_quote`: the official sentence(s), verbatim, short. `fiscal_source`: URL plus page.
- `notes`: anything a reviewer would need, including a disagreement with the current row.
Keep `measure_id` exactly as given unless the row must be split (see your brief); for a split, give new ids of the form `<old id>-A`, `-B`, and so on.

**Interactions.** List every pair of measures in the same state whose fiscal effects depend on each other (contingent receipts, overlapping refunds, competing measures), with the official text that says so and the joint figures if the analysis gives them.

**End with** a short summary: counts by new category, every row whose category changed and why, and anything you could not verify (with what you tried).
