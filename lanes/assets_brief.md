# Lane brief: state-specific municipal bond funds with daily or intraday prices

Read `lanes/_common.md` first; its rules apply.

**Purpose.** For each state below, find every U.S.-listed or U.S.-registered fund whose portfolio is concentrated in that state's municipal bonds. The fund's price is the asset the event study will test. A state with no such fund is a recorded gap.

**States:** AK, AL, AR, AZ, CA, CO, FL, GA, HI, IA, ID, IN, KS, KY, LA, MA, MD, MN, MO, MT, NC, ND, NE, NH, NM, NV, OH, OK, RI, SD, TN, TX, UT, VA, VT, WA, WI, WV, WY. Also NJ, NY, PA, MI, CT, OR and SC, for completeness of the national map.

**For each fund, from the sponsor's own product page or prospectus:**
- ticker, full name, sponsor, and type: ETF, closed-end fund, or open-end mutual fund (give the share class with the longest history);
- net assets and as-of date; effective or modified duration; share of assets in the named state's bonds; leverage, for closed-end funds;
- whether it is still operating (not merged or liquidated), and its inception date;
- price frequency: ETFs and closed-end funds trade intraday; mutual funds strike one NAV a day. Note whether the fund's evaluated-pricing vendor is disclosed.

**Also list national benchmarks** with the same fields: iShares MUB, Vanguard VTEB, SPDR TFI, and the three largest national municipal closed-end funds by assets.

**Output tables:** (a) one row per state-specific fund; (b) one row per state: best intraday instrument (ETF, else closed-end fund), best daily instrument, or "none"; (c) national benchmarks; (d) gaps and UNVERIFIED items. Leave out any fund you could not confirm on a sponsor page, and list it in (d).
